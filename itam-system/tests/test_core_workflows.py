import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
import app.models  # noqa: F401
from app.models.asset import Asset
from app.models.checkout import AssetCheckout
from app.models.product import DeviceType, ProductCatalog
from app.models.purchase import Purchase, PurchaseItem
from app.models.repair import RepairRecord
from app.models.scan_binding import AssetScanBinding
from app.core.schema_compat import current_timestamp_sql
from app.schemas.asset import AssetBatchImport, AssetBatchUpdateCreate, AssetImportRow, AssetUpdate
from app.schemas.purchase import PurchaseAcceptanceReceive
from app.schemas.repair import RepairCreate
from app.schemas.user import UserPermissionUpdate, UserUpsert
from app.services.asset_service import AssetService, AssetValidationError
from app.services.dashboard_service import DashboardService
from app.services.identity_service import IdentityService
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService
from app.services.scrap_service import ScrapService
from app.services.todo_service import TodoService


class CoreWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_asset(self, asset_id="ITAM-000001", dept_id="D1", status="in_stock"):
        asset = Asset(
            asset_id=asset_id,
            asset_no=asset_id,
            name="Test asset",
            category="Laptop",
            dept_id=dept_id,
            status=status,
        )
        self.db.add(asset)
        self.db.commit()
        return asset

    def test_department_scope_blocks_cross_department_update(self):
        self.add_asset(dept_id="D2")
        context = {"role": "dept_manager", "dept_id": "D1", "user_id": "manager-1"}
        with self.assertRaises(ValueError):
            AssetService.update_asset(self.db, "ITAM-000001", AssetUpdate(name="Changed"), "manager", context)

    def test_asset_manager_can_manage_all_assets(self):
        self.add_asset(dept_id="D2")
        context = {"role": "asset_manager", "user_id": "asset-manager"}
        row = AssetService.get_scoped_asset(self.db, "ITAM-000001", context)
        self.assertEqual(row.dept_id, "D2")

    def test_asset_rename_updates_checkout_and_scan_binding(self):
        asset = self.add_asset()
        self.db.add(AssetCheckout(asset_id=asset.asset_id, checkout_type="in_use", checked_out_by="tester"))
        self.db.add(AssetScanBinding(asset_id=asset.asset_id, scan_key="qr-1", scan_raw="qr-1"))
        self.db.commit()

        AssetService.update_asset(
            self.db,
            asset.asset_id,
            AssetUpdate(asset_id="ITAM-000099"),
            "tester",
            {"role": "admin"},
        )

        self.assertIsNotNone(self.db.get(Asset, "ITAM-000099"))
        self.assertEqual(self.db.query(AssetCheckout).one().asset_id, "ITAM-000099")
        self.assertEqual(self.db.query(AssetScanBinding).one().asset_id, "ITAM-000099")

    def test_invalid_status_transition_is_rejected(self):
        with self.assertRaises(AssetValidationError):
            AssetService.validate_transition("in_stock", "disposed")
        AssetService.validate_transition("in_stock", "in_use")

    def test_purchase_acceptance_requires_exact_quantity(self):
        purchase = Purchase(purchase_no="PO-1", status="pending_acceptance")
        purchase.items.append(PurchaseItem(name="Laptop", category="Laptop", quantity=2, unit_price=100))
        self.db.add(purchase)
        self.db.commit()
        payload = PurchaseAcceptanceReceive(
            operator="tester",
            acceptances=[{"item_id": purchase.items[0].id, "assets": [{"asset_id": "ITAM-10"}]}],
        )
        with self.assertRaisesRegex(ValueError, "must equal purchase quantity"):
            PurchaseService.accept_purchase(self.db, purchase.purchase_no, payload, {"role": "admin"})

    def test_purchase_acceptance_respects_department_scope(self):
        purchase = Purchase(purchase_no="PO-D2", status="pending_acceptance")
        purchase.items.append(PurchaseItem(name="Laptop", category="Laptop", quantity=1, unit_price=100, dept_id="D2"))
        self.db.add(purchase)
        self.db.commit()
        payload = PurchaseAcceptanceReceive(
            operator="tester",
            acceptances=[{"item_id": purchase.items[0].id, "assets": [{"asset_id": "ITAM-20"}]}],
        )
        with self.assertRaises(ValueError):
            PurchaseService.accept_purchase(
                self.db,
                purchase.purchase_no,
                payload,
                {"role": "dept_manager", "dept_id": "D1", "user_id": "manager-1"},
            )

    def test_repair_rejects_second_active_record(self):
        asset = self.add_asset()
        self.db.add(
            RepairRecord(
                repair_no="RP-2026-0001",
                asset_id=asset.asset_id,
                repair_time=datetime.utcnow(),
                fault_reason="Power",
                operator="tester",
                status="维修中",
            )
        )
        self.db.commit()
        payload = RepairCreate(asset_id=asset.asset_id, repair_time=datetime.utcnow(), fault_reason="Screen")
        with self.assertRaisesRegex(ValueError, "active repair"):
            RepairService.create_record(self.db, payload, {"role": "admin"})

    def test_enterprise_dashboard_uses_backend_aggregation(self):
        self.add_asset(asset_id="ITAM-DASH-1", status="in_stock")
        self.add_asset(asset_id="ITAM-DASH-2", status="repair")

        result = DashboardService.enterprise(self.db, {"role": "admin"})
        metrics = {item["label"]: item["value"] for item in result["metrics"]}

        self.assertEqual(metrics["在管资产"], 2)
        self.assertTrue(any(item["name"] == "库存中" and item["value"] == 1 for item in result["lifecycleDistribution"]))
        self.assertTrue(any(item["name"] == "笔记本电脑" and item["value"] == 2 for item in result["categoryDistribution"]))

    def test_todo_service_caches_short_lived_list(self):
        TodoService.invalidate()
        purchase = Purchase(purchase_no="PO-TODO-1", status="pending_acceptance")
        purchase.items.append(PurchaseItem(name="Laptop", category="Laptop", quantity=1, unit_price=100))
        self.db.add(purchase)
        self.db.commit()

        first = TodoService.list_todos(self.db, {"role": "admin"})
        self.db.add(Purchase(purchase_no="PO-TODO-2", status="pending_acceptance"))
        self.db.commit()
        second = TodoService.list_todos(self.db, {"role": "admin"})
        TodoService.invalidate()
        third = TodoService.list_todos(self.db, {"role": "admin"})

        self.assertEqual(len(first), len(second))
        self.assertGreater(len(third), len(second))

    def test_batch_update_rolls_back_when_any_asset_fails(self):
        self.add_asset(asset_id="ITAM-BATCH-1")
        self.add_asset(asset_id="ITAM-BATCH-2", status="scrapped")

        result = AssetService.batch_update_assets(
            self.db,
            AssetBatchUpdateCreate(asset_ids=["ITAM-BATCH-1", "ITAM-BATCH-2"], updates=AssetUpdate(location="New room")),
            "tester",
            {"role": "admin"},
        )

        self.assertEqual(result["success"], 0)
        self.assertEqual(self.db.get(Asset, "ITAM-BATCH-1").location, None)

    def test_sqlite_timestamp_compat_uses_current_timestamp(self):
        self.assertEqual(current_timestamp_sql(self.engine), "CURRENT_TIMESTAMP")

    def test_scrap_disposal_keeps_asset_status_scrapped(self):
        asset = self.add_asset(asset_id="ITAM-SCRAP-1")
        request = ScrapService.create_request(
            self.db,
            asset.asset_id,
            {"reason": "retired"},
            "tester",
            {"role": "admin"},
        )

        disposed = ScrapService.dispose(
            self.db,
            request.id,
            {
                "retirement_approval_no": "SC-APPROVAL-1",
                "disposal_method": "报废",
                "final_residual_value": 10,
                "disposal_remark": "disposed by recycling",
            },
            "tester",
            {"role": "admin"},
        )

        self.assertEqual(disposed.status, "已处置")
        self.assertEqual(self.db.get(Asset, asset.asset_id).status, "scrapped")


    def test_external_user_sync_preserves_manual_role(self):
        user, created = IdentityService.upsert_user(
            self.db,
            UserUpsert(
                username="ldap-user",
                display_name="LDAP User",
                role="user",
                source="ldap",
                external_id="ldap:uid=ldap-user,dc=example,dc=com",
            ),
        )
        self.assertTrue(created)
        self.assertEqual(user.role, "user")

        IdentityService.update_user_permissions(
            self.db,
            user.user_id,
            UserPermissionUpdate(role="asset_manager", status="active"),
        )

        synced_user, created = IdentityService.upsert_user(
            self.db,
            UserUpsert(
                username="ldap-user",
                display_name="LDAP User Updated",
                role="user",
                source="ldap",
                external_id="ldap:uid=ldap-user,dc=example,dc=com",
                dept_id="D2",
            ),
        )

        self.assertFalse(created)
        self.assertEqual(synced_user.role, "asset_manager")
        self.assertEqual(synced_user.dept_id, "D2")

    def test_import_preserves_payment_metadata(self):
        row = AssetService.normalize_import_row(
            AssetImportRow(
                asset_id="OLD-001",
                asset_no="OLD-001",
                name="Legacy Asset",
                category="Laptop",
                payment_time="2026-07-21",
                payment_no="PAY-001",
            )
        )

        self.assertEqual(row.asset_id, "OLD-001")
        self.assertEqual(row.asset_no, "OLD-001")
        self.assertEqual(row.config["payment_time"], "2026-07-21")
        self.assertEqual(row.config["payment_no"], "PAY-001")

    def test_overwrite_import_updates_existing_asset_by_asset_no_and_renames_id(self):
        self.add_asset(asset_id="ITAM-000001")
        existing = self.db.get(Asset, "ITAM-000001")
        existing.asset_no = "TAG-001"
        self.db.commit()

        result = AssetService.import_assets(
            self.db,
            AssetBatchImport(
                overwrite=True,
                items=[
                    AssetImportRow(
                        asset_id="LEGACY-001",
                        asset_no="TAG-001",
                        name="Updated legacy asset",
                        category="Monitor",
                        status="in_stock",
                    )
                ],
            ),
        )

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertIsNone(self.db.get(Asset, "ITAM-000001"))
        updated = self.db.get(Asset, "LEGACY-001")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.asset_no, "TAG-001")
        self.assertEqual(updated.name, "Updated legacy asset")

    def test_import_creates_product_catalog_without_duplicates(self):
        payload = AssetBatchImport(
            overwrite=True,
            items=[
                AssetImportRow(
                    asset_id="LEGACY-002",
                    asset_no="TAG-002",
                    name="ThinkPad X1 Carbon",
                    category="笔记本电脑",
                    brand="Lenovo",
                    model="X1 Carbon Gen 12",
                    spec="Ultra 7 / 32GB / 1TB",
                    purchase_price=15000,
                    location="阳光粤海大厦",
                    status="in_stock",
                )
            ],
        )

        first = AssetService.import_assets(self.db, payload)
        second = AssetService.import_assets(self.db, payload)

        self.assertEqual(first["created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(self.db.query(DeviceType).filter(DeviceType.name == "笔记本电脑").count(), 1)
        catalogs = self.db.query(ProductCatalog).filter(
            ProductCatalog.product_name == "ThinkPad X1 Carbon",
            ProductCatalog.device_type == "笔记本电脑",
        ).all()
        self.assertEqual(len(catalogs), 1)
        self.assertEqual(catalogs[0].brand, "Lenovo")
        self.assertEqual(catalogs[0].model, "X1 Carbon Gen 12")
        self.assertEqual(catalogs[0].spec, "Ultra 7 / 32GB / 1TB")
        self.assertEqual(catalogs[0].unit_price, 15000)
        self.assertEqual(catalogs[0].default_warehouse, "阳光粤海大厦")


if __name__ == "__main__":
    unittest.main()
