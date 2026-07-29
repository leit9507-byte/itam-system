import unittest
from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.core.database import Base
import app.models  # noqa: F401
from app.models.asset import Asset
from app.models.checkout import AssetCheckout
from app.models.company import Company
from app.models.lifecycle import Lifecycle
from app.models.product import DeviceType, ProductCatalog
from app.models.purchase import Purchase, PurchaseItem
from app.models.repair import RepairRecord
from app.models.scan_binding import AssetScanBinding
from app.models.scrap import ScrapRequest
from app.models.stocktake import StocktakeItem, StocktakeTask
from app.models.user import UserDirectory
from app.api.stocktake import StocktakeItemSubmit, submit_item
from app.api.company import list_companies, list_company_assets
from app.core.schema_compat import current_timestamp_sql
from app.schemas.asset import AssetBatchImport, AssetBatchUpdateCreate, AssetImportRow, AssetUpdate
from app.schemas.purchase import PurchaseAcceptanceReceive
from app.schemas.repair import RepairCreate
from app.schemas.user import UserPermissionUpdate, UserUpsert
from app.services.asset_service import AssetService, AssetValidationError
from app.services.asset_residual_service import AssetResidualService
from app.services.dashboard_service import DashboardService
from app.services.identity_service import IdentityService
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService
from app.services.scrap_service import ScrapService
from app.services.todo_service import TodoService
from app.api.product import ensure_seed


class CoreWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        DashboardService._cache.clear()
        TodoService.invalidate()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_models_package_exports_clean_deploy_tables(self):
        self.assertTrue(hasattr(app.models, "Company"))
        self.assertTrue(hasattr(app.models, "Location"))
        self.assertTrue(hasattr(app.models, "ScrapRequest"))

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

    def test_company_read_endpoints_do_not_rewrite_asset_rows(self):
        asset = self.add_asset(asset_id="COMPANY-READ-001")
        asset.company = "  Example Company  "
        self.db.commit()

        companies = list_companies(self.db)
        assets = list_company_assets(company="Example Company", db=self.db)

        self.db.refresh(asset)
        self.assertEqual(asset.company, "  Example Company  ")
        self.assertTrue(any(item["name"] == "Example Company" for item in companies))
        self.assertEqual(assets["total"], 1)
        self.assertEqual(assets["list"][0]["asset_id"], "COMPANY-READ-001")

    def test_asset_manager_can_manage_all_assets(self):
        self.add_asset(dept_id="D2")
        context = {"role": "asset_manager", "user_id": "asset-manager"}
        row = AssetService.get_scoped_asset(self.db, "ITAM-000001", context)
        self.assertEqual(row.dept_id, "D2")

    def test_edit_allows_unchanged_legacy_status_owner_mismatch(self):
        asset = self.add_asset(status="in_stock")
        asset.owner_user_id = "legacy-owner"
        self.db.commit()

        result = AssetService.update_asset(
            self.db,
            asset.asset_id,
            AssetUpdate(name="Updated asset", status="in_stock", owner_user_id="legacy-owner"),
            "tester",
            {"role": "admin"},
        )

        self.assertEqual(result["name"], "Updated asset")
        self.assertEqual(result["owner_user_id"], "legacy-owner")

    def test_terminal_asset_allows_metadata_edit_when_workflow_fields_are_unchanged(self):
        asset = self.add_asset(status="disposed")
        asset.owner_user_id = "legacy-owner"
        asset.dept_id = "D1"
        asset.location = "archive"
        self.db.commit()

        result = AssetService.update_asset(
            self.db,
            asset.asset_id,
            AssetUpdate(
                name="Archived asset",
                status="disposed",
                owner_user_id="legacy-owner",
                dept_id="D1",
                location="archive",
            ),
            "tester",
            {"role": "admin"},
        )

        self.assertEqual(result["name"], "Archived asset")
        self.assertEqual(result["status"], "disposed")

    def test_mobile_stocktake_can_reconcile_asset_owner_and_location(self):
        self.db.add_all(
            [
                UserDirectory(user_id="U1", username="user1", display_name="User 1", dept_id="D1", status="active"),
                UserDirectory(user_id="U2", username="user2", display_name="User 2", dept_id="D2", status="active"),
            ]
        )
        asset = self.add_asset(status="in_use")
        asset.owner_user_id = "U1"
        asset.dept_id = "D1"
        asset.location = "Room A"
        task = StocktakeTask(id="ST-TEST-001", name="Test stocktake", status="进行中")
        task.items.append(
            StocktakeItem(
                asset_id=asset.asset_id,
                name=asset.name,
                book_status=asset.status,
                book_location=asset.location,
                book_owner_user_id=asset.owner_user_id,
                result="未盘",
            )
        )
        self.db.add(task)
        self.db.commit()

        request = Request({"type": "http", "method": "POST", "path": "/stocktake/tasks/ST-TEST-001/items/ITAM-000001", "headers": []})
        request.state.user = {
            "user_id": "admin",
            "username": "admin",
            "display_name": "Admin",
            "role": "admin",
        }
        result = submit_item(
            task.id,
            asset.asset_id,
            StocktakeItemSubmit(
                actual_location="Room B",
                actual_owner_user_id="U2",
                update_asset_info=True,
                result="正常",
            ),
            request,
            self.db,
        )

        self.db.refresh(asset)
        self.assertEqual(asset.owner_user_id, "U2")
        self.assertEqual(asset.dept_id, "D2")
        self.assertEqual(asset.location, "Room B")
        self.assertEqual(result["result"], "使用人不符")
        self.assertTrue(result["asset_info_updated"])
        self.assertEqual(result["review_status"], "已确认")

        lifecycle_count = self.db.query(Lifecycle).filter(Lifecycle.asset_id == asset.asset_id).count()
        repeated = submit_item(
            task.id,
            asset.asset_id,
            StocktakeItemSubmit(
                actual_location="Room B",
                actual_owner_user_id="U2",
                update_asset_info=True,
                result="正常",
            ),
            request,
            self.db,
        )
        self.assertFalse(repeated["asset_info_updated"])
        self.assertEqual(repeated["review_status"], "已确认")
        self.assertEqual(self.db.query(Lifecycle).filter(Lifecycle.asset_id == asset.asset_id).count(), lifecycle_count)

    def test_asset_residual_methods_use_distinct_curves_and_minimum_floor(self):
        base_config = {
            "minimum_residual_rate": 0.05,
            "missing_basis_policy": "original",
            "category_rates": [],
        }
        values = {
            method: AssetResidualService.calculate(
                10000,
                date(2020, 1, 1),
                5,
                date(2022, 1, 1),
                {**base_config, "method": method},
            )
            for method in AssetResidualService.VALID_METHODS
        }

        self.assertLess(values["fixed_rate"], values["double_declining"])
        self.assertLess(values["double_declining"], values["sum_of_years_digits"])
        self.assertLess(values["sum_of_years_digits"], values["straight_line"])
        for method in AssetResidualService.VALID_METHODS:
            expired = AssetResidualService.calculate(
                10000,
                date(2020, 1, 1),
                5,
                date(2030, 1, 1),
                {**base_config, "method": method},
            )
            self.assertEqual(expired, 500)

    def test_asset_residual_method_is_persisted(self):
        saved = AssetResidualService.save_config(
            self.db,
            {
                "method": "double_declining",
                "minimum_residual_rate": 0.08,
                "missing_basis_policy": "original",
                "category_rates": [{"category": "Laptop", "minimum_residual_rate": 0.1}],
            },
            "tester",
        )

        self.assertEqual(saved["method"], "double_declining")
        loaded = AssetResidualService.get_config(self.db)
        self.assertEqual(loaded["method"], "double_declining")
        self.assertEqual(loaded["category_rates"][0]["minimum_residual_rate"], 0.1)

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

    def test_dashboard_product_retirement_index_matches_asset(self):
        product = ProductCatalog(product_name="ThinkPad X1 Carbon", device_type="Laptop", brand="Lenovo", model="Gen 12", retirement_years=4)
        asset = Asset(asset_id="ITAM-RET-001", name="ThinkPad X1 Carbon", brand="Lenovo", model="Gen 12")

        product_index = DashboardService.product_retirement_index([product])

        self.assertEqual(DashboardService.resolve_retirement_years(asset, product_index), 4)

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

    def test_onboarding_todo_skips_users_with_existing_imported_asset_owner(self):
        self.db.add(UserDirectory(user_id="U-ONBOARD-1", username="alice", display_name="Alice Zhang", status="active"))
        self.db.add(Asset(asset_id="ITAM-ONBOARD-1", asset_no="ITAM-ONBOARD-1", name="Laptop", category="Laptop", status="in_use", owner_user_id="alice-Alice Zhang"))
        self.db.commit()

        todos = TodoService.list_todos(self.db, {"role": "admin"})

        self.assertFalse(any(item["type"] == "onboarding_assign" and item.get("user_id") == "U-ONBOARD-1" for item in todos))

    def test_onboarding_todo_uses_all_assigned_assets_not_only_recent_limit(self):
        self.db.add(UserDirectory(user_id="U-ONBOARD-OLD", username="yukiko", display_name="廖玉连", status="active"))
        for index in range(TodoService.SOURCE_LIMIT + 5):
            self.db.add(
                Asset(
                    asset_id=f"ITAM-FILL-{index:04d}",
                    asset_no=f"ITAM-FILL-{index:04d}",
                    name="Fill asset",
                    category="Laptop",
                    status="in_stock",
                )
            )
        self.db.add(
            Asset(
                asset_id="ITAM-OLD-OWNER",
                asset_no="ITAM-OLD-OWNER",
                name="Desktop",
                category="Desktop",
                status="in_use",
                owner_user_id="yukiko-廖玉连",
            )
        )
        self.db.commit()

        todos = TodoService.list_todos(self.db, {"role": "admin"})

        self.assertFalse(any(item["type"] == "onboarding_assign" and item.get("user_id") == "U-ONBOARD-OLD" for item in todos))

    def test_onboarding_todo_skips_users_marked_no_asset_required(self):
        self.db.add(
            UserDirectory(
                user_id="U-ONBOARD-2",
                username="bob",
                display_name="Bob Li",
                status="active",
                asset_assignment_required=False,
            )
        )
        self.db.commit()

        todos = TodoService.list_todos(self.db, {"role": "admin"})

        self.assertFalse(any(item["type"] == "onboarding_assign" and item.get("user_id") == "U-ONBOARD-2" for item in todos))

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

    def test_row_mapping_preserves_company_from_english_header(self):
        row = AssetService.row_from_mapping(
            {
                "asset_id": "2232",
                "asset_no": "99-MB-20260521-001",
                "name": "手机-OPPO手机 A55",
                "category": "手机平板",
                "company": "深圳市九九互动科技有限公司",
            }
        )

        self.assertEqual(row.asset_id, "2232")
        self.assertEqual(row.asset_no, "99-MB-20260521-001")
        self.assertEqual(row.company, "深圳市九九互动科技有限公司")

    def test_row_mapping_parses_multiple_scan_codes(self):
        row = AssetService.normalize_import_row(
            AssetService.row_from_mapping(
                {
                    "资产编码": "QR-IMPORT-001",
                    "资产名称": "二维码导入资产",
                    "设备类型": "显示器",
                    "状态": "已报废",
                    "二维码内容": "QR-CODE-A\nQR-CODE-B；QR-CODE-A",
                }
            )
        )

        self.assertEqual(row.scan_codes, ["QR-CODE-A", "QR-CODE-B"])
        self.assertEqual(row.status, "scrapped")

    def test_row_mapping_parses_status_workflow_times(self):
        row = AssetService.row_from_mapping(
            {
                "资产名称": "借用设备",
                "设备类型": "笔记本电脑",
                "状态": "借用",
                "状态发生时间": "2026-07-01 09:30:00",
                "计划归还时间": "2026-07-31 18:00:00",
            }
        )

        self.assertEqual(row.status_time, datetime(2026, 7, 1, 9, 30))
        self.assertEqual(row.borrow_due_date, datetime(2026, 7, 31, 18, 0))

    def test_import_template_contains_scan_codes_and_correct_status_column(self):
        workbook = load_workbook(BytesIO(AssetService.build_import_template()))
        sheet = workbook["资产导入"]
        example = workbook["填写示例"]
        headers = [cell.value for cell in sheet[1]]

        self.assertIn("scan_codes", headers)
        self.assertEqual(
            headers[-5:],
            [
                "status_time",
                "borrow_due_date",
                "disposal_method",
                "retirement_approval_no",
                "dispose_recipient_name",
            ],
        )
        self.assertEqual(example["B2"].value, "NB-001")
        self.assertEqual(example["C2"].value, "ThinkPad X1 Carbon")
        self.assertEqual(example["V2"].value, "https://asset.example/nb-001")
        self.assertEqual(example["W2"].value, "2026-06-24 09:00:00")
        validations = [str(item.sqref) for item in sheet.data_validations.dataValidation]
        self.assertIn("M2:M500", validations)

    def test_import_creates_scan_bindings_and_scrap_request(self):
        payload = AssetBatchImport(
            overwrite=True,
            items=[
                AssetImportRow(
                    asset_id="OLD-SCRAP-QR-001",
                    asset_no="OLD-SCRAP-QR-001",
                    name="历史报废显示器",
                    category="显示器",
                    status="scrapped",
                    scan_codes=["QR-SCRAP-A", "QR-SCRAP-B"],
                )
            ],
        )

        first = AssetService.import_assets(self.db, payload)
        second = AssetService.import_assets(self.db, payload)

        self.assertEqual(first["created"], 1)
        self.assertEqual(first["scan_bindings_created"], 2)
        self.assertEqual(first["scrap_requests_created"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(second["scan_bindings_created"], 0)
        self.assertEqual(second["scrap_requests_created"], 0)
        self.assertEqual(
            self.db.query(AssetScanBinding)
            .filter(AssetScanBinding.asset_id == "OLD-SCRAP-QR-001", AssetScanBinding.status == "active")
            .count(),
            2,
        )
        scraps = self.db.query(ScrapRequest).filter(ScrapRequest.asset_id == "OLD-SCRAP-QR-001").all()
        self.assertEqual(len(scraps), 1)
        self.assertEqual(scraps[0].status, "待处置")
        self.assertTrue(scraps[0].retirement_flow_no)

    def test_import_creates_checkout_workflow_without_duplicates(self):
        status_time = datetime(2026, 7, 1, 9, 30)
        due_date = datetime(2026, 7, 31, 18, 0)
        payload = AssetBatchImport(
            overwrite=True,
            items=[
                AssetImportRow(
                    asset_id="BORROW-IMPORT-001",
                    name="导入借用设备",
                    category="笔记本电脑",
                    status="borrowed",
                    owner_user_id="U-IMPORT",
                    status_time=status_time,
                    borrow_due_date=due_date,
                )
            ],
        )

        first = AssetService.import_assets(self.db, payload)
        second = AssetService.import_assets(self.db, payload)
        checkout = self.db.query(AssetCheckout).filter(AssetCheckout.asset_id == "BORROW-IMPORT-001").one()

        self.assertEqual(first["checkout_records_created"], 1)
        self.assertEqual(second["checkout_records_created"], 0)
        self.assertEqual(checkout.checkout_type, "borrowed")
        self.assertEqual(checkout.checked_out_at, status_time)
        self.assertEqual(checkout.due_date, due_date)
        self.assertEqual(checkout.status, "open")

    def test_import_creates_repair_workflow_without_duplicates(self):
        status_time = datetime(2026, 7, 2, 10, 0)
        payload = AssetBatchImport(
            overwrite=True,
            items=[
                AssetImportRow(
                    asset_id="REPAIR-IMPORT-001",
                    name="导入维修设备",
                    category="显示器",
                    status="repair",
                    status_time=status_time,
                    remark="屏幕无显示",
                )
            ],
        )

        first = AssetService.import_assets(self.db, payload)
        second = AssetService.import_assets(self.db, payload)
        repair = self.db.query(RepairRecord).filter(RepairRecord.asset_id == "REPAIR-IMPORT-001").one()

        self.assertEqual(first["repair_records_created"], 1)
        self.assertEqual(second["repair_records_created"], 0)
        self.assertEqual(repair.repair_time, status_time)
        self.assertEqual(repair.status, "维修中")
        self.assertEqual(repair.fault_reason, "屏幕无显示")

    def test_import_disposed_asset_creates_completed_disposal_record(self):
        status_time = datetime(2026, 7, 3, 11, 0)
        result = AssetService.import_assets(
            self.db,
            AssetBatchImport(
                items=[
                    AssetImportRow(
                        asset_id="DISPOSED-IMPORT-001",
                        name="历史已处置设备",
                        category="显示器",
                        status="disposed",
                        status_time=status_time,
                        disposal_method="员工领用",
                        retirement_approval_no="RT-LEGACY-001",
                        dispose_recipient_name="张三",
                        remark="历史处置记录",
                    )
                ]
            ),
        )
        request = self.db.query(ScrapRequest).filter(ScrapRequest.asset_id == "DISPOSED-IMPORT-001").one()

        self.assertEqual(result["scrap_requests_created"], 1)
        self.assertEqual(request.status, "已处置")
        self.assertEqual(request.retirement_date, status_time)
        self.assertEqual(request.disposed_at, status_time)
        self.assertEqual(request.disposal_method, "员工领用")
        self.assertEqual(request.retirement_approval_no, "RT-LEGACY-001")
        self.assertEqual(request.dispose_recipient_name, "张三")
        self.assertIn("历史处置记录", request.disposal_remark)

    def test_import_scan_binding_conflict_rolls_back_asset(self):
        self.add_asset(asset_id="BOUND-ASSET-001")
        self.db.add(
            AssetScanBinding(
                asset_id="BOUND-ASSET-001",
                scan_key="shared-qr-code",
                scan_raw="SHARED-QR-CODE",
                scan_type="qrcode",
                status="active",
            )
        )
        self.db.commit()

        result = AssetService.import_assets(
            self.db,
            AssetBatchImport(
                items=[
                    AssetImportRow(
                        asset_id="CONFLICT-ASSET-001",
                        name="冲突资产",
                        category="显示器",
                        status="in_stock",
                        scan_codes=["SHARED-QR-CODE"],
                    )
                ]
            ),
        )

        self.assertEqual(result["created"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("已绑定其他资产", result["errors"][0]["message"])
        self.assertIsNone(self.db.get(Asset, "CONFLICT-ASSET-001"))

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
                    company="雷泰科技",
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
        self.assertEqual(self.db.query(Company).filter(Company.name == "雷泰科技").count(), 1)

    def test_product_seed_keeps_catalog_clean(self):
        ensure_seed(self.db)

        self.assertEqual(self.db.query(DeviceType).count(), 0)
        self.assertEqual(self.db.query(ProductCatalog).count(), 0)

    def test_product_seed_keeps_existing_device_type(self):
        self.db.add(DeviceType(name="笔记本电脑", description="已有类型"))
        self.db.commit()

        ensure_seed(self.db)

        self.assertEqual(self.db.query(DeviceType).filter(DeviceType.name == "笔记本电脑").count(), 1)
        self.assertEqual(self.db.query(ProductCatalog).count(), 0)

    def test_import_allows_historical_terminal_statuses(self):
        result = AssetService.import_assets(
            self.db,
            AssetBatchImport(
                items=[
                    AssetImportRow(asset_id="OLD-SCRAP-001", name="报废历史资产", category="显示器", status="scrapped"),
                    AssetImportRow(asset_id="OLD-DISP-001", name="已处置历史资产", category="手机", status="disposed"),
                    AssetImportRow(asset_id="OLD-LOST-001", name="丢失历史资产", category="手机", status="lost"),
                ],
            ),
        )

        self.assertEqual(result["created"], 3)
        self.assertEqual(self.db.get(Asset, "OLD-SCRAP-001").status, "scrapped")
        self.assertEqual(self.db.get(Asset, "OLD-DISP-001").status, "disposed")
        self.assertEqual(self.db.get(Asset, "OLD-LOST-001").status, "lost")
        with self.assertRaises(AssetValidationError):
            AssetService.ensure_asset_operable(self.db.get(Asset, "OLD-LOST-001"), "维修")


if __name__ == "__main__":
    unittest.main()
