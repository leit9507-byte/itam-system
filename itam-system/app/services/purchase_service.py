from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.purchase import Purchase, PurchaseItem
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseCreate
from app.services.asset_service import AssetService
from app.services.lifecycle_service import LifecycleService


class PurchaseService:
    @staticmethod
    def list_purchases(db: Session) -> list[Purchase]:
        return db.query(Purchase).order_by(Purchase.id.desc()).all()

    @staticmethod
    def create_purchase(db: Session, payload: PurchaseCreate) -> Purchase:
        purchase = Purchase(
            purchase_no=payload.purchase_no,
            supplier_name=payload.supplier_name,
            total_amount=payload.total_amount,
            status=payload.status,
        )
        db.add(purchase)
        db.flush()

        for item in payload.items:
            db.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    name=item.name,
                    category=item.category,
                    brand=item.brand,
                    model=item.model,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    location=item.location,
                    dept_id=item.dept_id,
                )
            )

        db.commit()
        db.refresh(purchase)
        return purchase

    @staticmethod
    def receive_purchase(db: Session, purchase_no: str, operator: str = "system") -> dict:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        if not purchase:
            raise ValueError("purchase not found")
        if purchase.status == "received":
            return {"purchase": purchase, "assets": []}

        created_assets: list[Asset] = []
        for item in purchase.items:
            for _ in range(item.quantity):
                asset = Asset(
                    asset_id=AssetService.generate_asset_id(db),
                    name=item.name,
                    category=item.category,
                    brand=item.brand,
                    model=item.model,
                    sn=None,
                    config={},
                    purchase_price=item.unit_price,
                    status="in_stock",
                    owner_user_id=None,
                    dept_id=item.dept_id,
                    location=item.location,
                )
                db.add(asset)
                db.flush()
                LifecycleService.record(db, asset.asset_id, "PURCHASE", None, "in_stock", operator)
                created_assets.append(asset)

        purchase.status = "received"
        db.commit()
        db.refresh(purchase)
        return {"purchase": purchase, "assets": created_assets}

    @staticmethod
    def accept_purchase(db: Session, purchase_no: str, payload: PurchaseAcceptanceReceive) -> dict:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        if not purchase:
            raise ValueError("purchase not found")
        if purchase.status == "received":
            return {"purchase": purchase, "assets": []}

        item_map = {item.id: item for item in purchase.items}
        created_assets: list[Asset] = []
        for acceptance in payload.acceptances:
            item = item_map.get(acceptance.item_id)
            if not item:
                raise ValueError(f"purchase item not found: {acceptance.item_id}")

            if len(acceptance.assets) > item.quantity:
                raise ValueError(f"accepted asset count exceeds quantity for item {item.id}")

            for accepted in acceptance.assets:
                if accepted.sn and db.query(Asset).filter(Asset.sn == accepted.sn).first():
                    raise ValueError(f"duplicate sn: {accepted.sn}")
                config = {}
                if accepted.spec:
                    config["spec"] = accepted.spec
                config["purchase_no"] = purchase.purchase_no
                config["purchase_item_id"] = item.id
                asset = Asset(
                    asset_id=AssetService.generate_asset_id(db),
                    name=accepted.name or item.name,
                    category=accepted.category or item.category,
                    brand=accepted.brand if accepted.brand is not None else item.brand,
                    model=accepted.model if accepted.model is not None else item.model,
                    sn=accepted.sn,
                    config=config,
                    purchase_price=accepted.purchase_price if accepted.purchase_price is not None else item.unit_price,
                    status="in_stock",
                    owner_user_id=accepted.owner_user_id,
                    dept_id=accepted.dept_id if accepted.dept_id is not None else item.dept_id,
                    location=accepted.location if accepted.location is not None else item.location,
                )
                db.add(asset)
                db.flush()
                LifecycleService.record(db, asset.asset_id, "PURCHASE_ACCEPTANCE", None, "in_stock", payload.operator)
                created_assets.append(asset)

        purchase.status = "received"
        db.commit()
        db.refresh(purchase)
        return {"purchase": purchase, "assets": created_assets}
