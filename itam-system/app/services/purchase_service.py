from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.purchase import Purchase, PurchaseItem
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseCreate
from app.services.asset_service import AssetService
from app.services.audit_log_service import AuditLogService
from app.services.lifecycle_service import LifecycleService
from app.services.notification_service import NotificationService
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
            status="pending_acceptance",
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
                    spec=item.spec,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    retirement_years=item.retirement_years,
                    purchase_reason=item.purchase_reason or payload.purchase_reason,
                    location=item.location,
                    dept_id=item.dept_id,
                )
            )

        AuditLogService.record_operation(db, "purchase", "create", "system", "purchase", purchase.purchase_no, f"创建采购单 {purchase.purchase_no}，进入验收", payload.model_dump())
        db.commit()
        db.refresh(purchase)
        NotificationService.send_event(
            db,
            "acceptance",
            "采购单待验收",
            [
                f"采购单号：{purchase.purchase_no}",
                f"审批单号：{purchase.approval_no or '-'}",
                f"供应商：{purchase.supplier_name or '-'}",
                f"采购金额：￥{purchase.total_amount or 0:,.0f}",
                "当前状态：待验收",
            ],
        )
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
                asset_id = AssetService.generate_asset_id(db)
                asset_no = AssetService.normalize_asset_no(None, asset_id)
                AssetService.validate_asset_identity_unique(db, asset_no=asset_no)
                asset = Asset(
                    asset_id=asset_id,
                    asset_no=asset_no,
                    name=item.name,
                    category=item.category,
                    brand=item.brand,
                    model=item.model,
                    sn=None,
                    config=PurchaseService.purchase_item_config(item),
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
                LifecycleService.record(
                    db,
                    asset.asset_id,
                    "PURCHASE",
                    None,
                    "in_stock",
                    operator,
                    LifecycleService.structured_remark(
                        reason=purchase.purchase_reason or "采购入库",
                        object=f"采购单 {purchase.purchase_no}",
                        previous_owner="-",
                        new_owner="-",
                        location=asset.location,
                        extra={
                            "purchase_no": purchase.purchase_no,
                            "supplier": purchase.supplier_name or "",
                            "dept_id": asset.dept_id or "",
                        },
                    ),
                )
                created_assets.append(asset)

        purchase.status = "received"
        AuditLogService.record_operation(db, "purchase", "receive", operator, "purchase", purchase.purchase_no, f"采购入库 {purchase.purchase_no}")
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
        default_purchase_date = datetime.utcnow()
        for acceptance in payload.acceptances:
            item = item_map.get(acceptance.item_id)
            if not item:
                raise ValueError(f"purchase item not found: {acceptance.item_id}")

            if len(acceptance.assets) > item.quantity:
                raise ValueError(f"accepted asset count exceeds quantity for item {item.id}")

            for accepted in acceptance.assets:
                asset_id = AssetService.normalize_blank(accepted.asset_id) or AssetService.generate_asset_id(db)
                if db.get(Asset, asset_id):
                    raise ValueError(f"duplicate asset_id: {asset_id}")
                asset_no = AssetService.normalize_asset_no(None, asset_id)
                sn = AssetService.normalize_blank(accepted.sn) or None
                AssetService.validate_asset_identity_unique(db, asset_no=asset_no, sn=sn)
                owner_user = AssetService.find_user(db, accepted.owner_user_id)
                owner_user_id = owner_user.user_id if owner_user else AssetService.normalize_blank(accepted.owner_user_id) or None
                config = {}
                spec = AssetService.normalize_blank(accepted.spec) or item.spec
                if spec:
                    config["spec"] = spec
                config["purchase_no"] = purchase.purchase_no
                config["purchase_item_id"] = item.id
                retirement_years = accepted.retirement_years if accepted.retirement_years is not None else item.retirement_years
                if retirement_years:
                    config["retirement_years"] = retirement_years
                asset = Asset(
                    asset_id=asset_id,
                    asset_no=asset_no,
                    name=accepted.name or item.name,
                    category=accepted.category or item.category,
                    brand=accepted.brand if accepted.brand is not None else item.brand,
                    model=accepted.model if accepted.model is not None else item.model,
                    sn=sn,
                    config=config,
                    company=AssetService.normalize_company(accepted.company) or purchase.company,
                    purchase_price=accepted.purchase_price if accepted.purchase_price is not None else item.unit_price,
                    purchase_date=accepted.purchase_date or default_purchase_date,
                    purchase_approval_no=accepted.purchase_approval_no or purchase.approval_no or purchase.purchase_no,
                    purchase_supplier_name=accepted.purchase_supplier_name or purchase.supplier_name,
                    warranty_expire_date=accepted.warranty_expire_date,
                    warranty_months=accepted.warranty_months,
                    status="in_use" if owner_user_id else "in_stock",
                    owner_user_id=owner_user_id,
                    dept_id=(owner_user.dept_id or owner_user.dept_name) if owner_user else (accepted.dept_id if accepted.dept_id is not None else item.dept_id),
                    location=accepted.location if accepted.location is not None else item.location,
                )
                AssetService.apply_warranty_expire(asset)
                db.add(asset)
                db.flush()
                LifecycleService.record(
                    db,
                    asset.asset_id,
                    "PURCHASE_ACCEPTANCE",
                    None,
                    "in_stock",
                    payload.operator,
                    LifecycleService.structured_remark(
                        reason=item.purchase_reason or purchase.purchase_reason or "采购验收入库",
                        object=f"采购单 {purchase.purchase_no}",
                        previous_owner="-",
                        new_owner=owner_user_id or "-",
                        location=asset.location,
                        extra={
                            "purchase_no": purchase.purchase_no,
                            "purchase_item_id": item.id,
                            "supplier": purchase.supplier_name or "",
                            "asset_no": asset.asset_no or "",
                            "sn": asset.sn or "",
                        },
                    ),
                )
                if owner_user_id:
                    LifecycleService.record(
                        db,
                        asset.asset_id,
                        "STATUS_CHANGE",
                        "in_stock",
                        asset.status,
                        payload.operator,
                        AssetService.inventory_lifecycle_remark(
                            asset.status,
                            "采购验收后直接分配",
                            None,
                            None,
                            owner_user_id,
                            owner_user,
                            asset.location,
                        ),
                    )
                    AssetService.sync_checkout_record(
                        db,
                        asset,
                        "in_stock",
                        asset.status,
                        payload.operator,
                        None,
                        None,
                        owner_user,
                        None,
                        "采购验收后直接分配",
                    )
                created_assets.append(asset)

        purchase.status = "received"
        AuditLogService.record_operation(db, "purchase", "accept", payload.operator, "purchase", purchase.purchase_no, f"采购验收 {purchase.purchase_no}")
        db.commit()
        db.refresh(purchase)
        NotificationService.send_event(
            db,
            "acceptance",
            "采购验收完成",
            [
                f"采购单号：{purchase.purchase_no}",
                f"本次入库资产：{len(created_assets)} 台",
                f"直接分配资产：{len([asset for asset in created_assets if asset.owner_user_id])} 台",
                f"供应商：{purchase.supplier_name or '-'}",
                f"操作人：{payload.operator}",
            ],
        )
        return {"purchase": purchase, "assets": created_assets}

    @staticmethod
    def purchase_item_config(item: PurchaseItem) -> dict:
        config = {}
        if item.spec:
            config["spec"] = item.spec
        if item.retirement_years:
            config["retirement_years"] = item.retirement_years
        return config
