import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
import app.models  # noqa: F401
from app.models.asset import Asset
from app.models.checkout import AssetCheckout
from app.models.purchase import Purchase, PurchaseItem
from app.models.repair import RepairRecord
from app.models.scan_binding import AssetScanBinding
from app.schemas.asset import AssetUpdate
from app.schemas.purchase import PurchaseAcceptanceReceive
from app.schemas.repair import RepairCreate
from app.services.asset_service import AssetService, AssetValidationError
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService


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


if __name__ == "__main__":
    unittest.main()
