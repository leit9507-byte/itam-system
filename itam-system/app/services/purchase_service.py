from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.purchase import Purchase, PurchaseItem
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseCreate
from app.services.asset_service import AssetService
from app.services.audit_log_service import AuditLogService
from app.services.lifecycle_service import LifecycleService
from app.services.supplier_service import SupplierService


class PurchaseService:
    @staticmethod
    def list_purchases(
        db: Session,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 0,
        user_context: dict | None = None,
    ) -> dict:
        query = db.query(Purchase)
        query = PurchaseService.apply_data_scope(query, user_context)
        if created_from:
            query = query.filter(Purchase.created_at >= created_from)
        if created_to:
            query = query.filter(Purchase.created_at <= created_to)
        total = query.count()
        query = query.order_by(Purchase.id.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        return {"list": query.all(), "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def apply_data_scope(query, user_context: dict | None):
        if can_view_all_data(user_context):
            return query
        dept_id = scoped_dept_id(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter(Purchase.items.any(PurchaseItem.dept_id == dept_id))
        identities = scoped_user_identities(user_context)
        if identities:
            return query.filter(Purchase.items.any(PurchaseItem.dept_id.in_(identities)))
        return query.filter(False)

    @staticmethod
    def create_purchase(db: Session, payload: PurchaseCreate) -> Purchase:
        purchase = Purchase(
            purchase_no=payload.purchase_no,
            company=AssetService.normalize_company(payload.company),
            approval_no=payload.approval_no,
            supplier_name=payload.supplier_name,
            purchase_reason=payload.purchase_reason,
            total_amount=payload.total_amount,
            status=payload.status,
        )
        SupplierService.ensure_supplier(db, payload.supplier_name)
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
                    retirement_years=item.retirement_years,
                    purchase_reason=item.purchase_reason or payload.purchase_reason,
                    location=item.location,
                    dept_id=item.dept_id,
                )
            )

        AuditLogService.record_operation(db, "purchase", "create", "system", "purchase", purchase.purchase_no, f"创建采购单 {purchase.purchase_no}", payload.model_dump())
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
        purchase_date = datetime.utcnow()
        for item in purchase.items:
            for _ in range(item.quantity):
                asset = Asset(
                    asset_id=AssetService.generate_asset_id(db),
                    name=item.name,
                    category=item.category,
                    brand=item.brand,
                    model=item.model,
                    sn=None,
                    config={"retirement_years": item.retirement_years} if item.retirement_years else {},
                    company=purchase.company,
                    purchase_price=item.unit_price,
                    purchase_date=purchase_date,
                    purchase_approval_no=purchase.approval_no or purchase.purchase_no,
                    purchase_supplier_name=purchase.supplier_name,
                    status="in_stock",
                    owner_user_id=None,
                    dept_id=item.dept_id,
                    location=item.location,
                )
                AssetService.apply_warranty_expire(asset)
                db.add(asset)
                db.flush()
                LifecycleService.record(db, asset.asset_id, "PURCHASE", None, "in_stock", operator)
                created_assets.append(asset)

        purchase.status = "received"
        AuditLogService.record_operation(db, "purchase", "receive", operator, "purchase", purchase.purchase_no, f"采购入库 {purchase.purchase_no}")
        db.commit()
        db.refresh(purchase)
        return {"purchase": purchase, "assets": created_assets}

    @staticmethod
    def approve_purchase(db: Session, purchase_no: str, operator: str = "system", allow_submitted: bool = False) -> Purchase:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        if not purchase:
            raise ValueError("purchase not found")
        if purchase.status == "received":
            raise ValueError("received purchase cannot be approved again")
        if purchase.status == "pending_acceptance":
            return purchase
        allowed = {"created", "approval_submitted"} if allow_submitted else {"created"}
        if purchase.status not in allowed:
            raise ValueError(f"purchase status cannot be approved: {purchase.status}")
        purchase.status = "pending_acceptance"
        AuditLogService.record_operation(db, "purchase", "approve", operator, "purchase", purchase.purchase_no, f"采购审批通过 {purchase.purchase_no}")
        db.commit()
        db.refresh(purchase)
        return purchase

    @staticmethod
    def mark_approval_submitted(db: Session, purchase_no: str, operator: str = "system") -> Purchase:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        if not purchase:
            raise ValueError("purchase not found")
        if purchase.status == "created":
            purchase.status = "approval_submitted"
            AuditLogService.record_operation(db, "purchase", "approval_submit", operator, "purchase", purchase.purchase_no, f"采购提交飞书审批 {purchase.purchase_no}")
            db.commit()
            db.refresh(purchase)
        return purchase

    @staticmethod
    def accept_purchase(db: Session, purchase_no: str, payload: PurchaseAcceptanceReceive) -> dict:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        if not purchase:
            raise ValueError("purchase not found")
        if purchase.status == "received":
            return {"purchase": purchase, "assets": []}

        item_map = {item.id: item for item in purchase.items}
        created_assets: list[Asset] = []
        default_purchase_date = datetime.utcnow()
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
                if item.retirement_years:
                    config["retirement_years"] = item.retirement_years
                asset = Asset(
                    asset_id=AssetService.generate_asset_id(db),
                    name=accepted.name or item.name,
                    category=accepted.category or item.category,
                    brand=accepted.brand if accepted.brand is not None else item.brand,
                    model=accepted.model if accepted.model is not None else item.model,
                    sn=accepted.sn,
                    config=config,
                    company=AssetService.normalize_company(accepted.company) or purchase.company,
                    purchase_price=accepted.purchase_price if accepted.purchase_price is not None else item.unit_price,
                    purchase_date=accepted.purchase_date or default_purchase_date,
                    purchase_approval_no=accepted.purchase_approval_no or purchase.approval_no or purchase.purchase_no,
                    purchase_supplier_name=accepted.purchase_supplier_name or purchase.supplier_name,
                    warranty_expire_date=accepted.warranty_expire_date,
                    warranty_months=accepted.warranty_months,
                    status="in_stock",
                    owner_user_id=accepted.owner_user_id,
                    dept_id=accepted.dept_id if accepted.dept_id is not None else item.dept_id,
                    location=accepted.location if accepted.location is not None else item.location,
                )
                AssetService.apply_warranty_expire(asset)
                db.add(asset)
                db.flush()
                LifecycleService.record(db, asset.asset_id, "PURCHASE_ACCEPTANCE", None, "in_stock", payload.operator)
                created_assets.append(asset)

        purchase.status = "received"
        AuditLogService.record_operation(db, "purchase", "accept", payload.operator, "purchase", purchase.purchase_no, f"采购验收 {purchase.purchase_no}")
        db.commit()
        db.refresh(purchase)
        return {"purchase": purchase, "assets": created_assets}
