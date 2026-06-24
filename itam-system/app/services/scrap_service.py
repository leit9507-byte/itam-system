from datetime import datetime

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.scrap import ScrapRequest
from app.services.lifecycle_service import LifecycleService


class ScrapService:
    @staticmethod
    def list_requests(db: Session) -> list[ScrapRequest]:
        return db.query(ScrapRequest).order_by(ScrapRequest.id.desc()).all()

    @staticmethod
    def create_request(db: Session, asset_id: str, payload: dict, operator: str = "资产管理员") -> ScrapRequest:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("asset not found")
        existed = db.query(ScrapRequest).filter(ScrapRequest.asset_id == asset_id, ScrapRequest.status == "审批中").first()
        if existed:
            return existed
        request = ScrapRequest(
            request_no=ScrapService.generate_no(db),
            asset_id=asset.asset_id,
            asset_name=asset.name,
            asset_sn=asset.sn,
            company=asset.company,
            category=asset.category,
            brand=asset.brand,
            model=asset.model,
            owner_user_id=asset.owner_user_id,
            dept_id=asset.dept_id,
            location=asset.location,
            purchase_price=asset.purchase_price,
            purchase_date=asset.purchase_date,
            purchase_approval_no=asset.purchase_approval_no,
            purchase_supplier_name=asset.purchase_supplier_name,
            applicant=payload.get("applicant") or asset.dept_id or operator,
            reason=payload.get("reason") or "",
            disposal_method=payload.get("disposal_method") or "环保回收",
            estimated_residual_value=float(payload.get("estimated_residual_value") or 0),
            status="审批中",
        )
        from_status = asset.status
        asset.status = "pending_scrap"
        db.add(request)
        LifecycleService.record(db, asset.asset_id, "SCRAP_REQUEST", from_status, "pending_scrap", operator, request.reason)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def approve(db: Session, request_id: int, approver: str) -> ScrapRequest:
        request = db.get(ScrapRequest, request_id)
        if not request:
            raise ValueError("scrap request not found")
        asset = db.get(Asset, request.asset_id)
        request.status = "已通过"
        request.approver = approver
        request.approved_at = datetime.utcnow()
        if asset:
            from_status = asset.status
            asset.status = "scrapped"
            LifecycleService.record(db, asset.asset_id, "SCRAP_APPROVE", from_status, "scrapped", approver, request.reason)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def reject(db: Session, request_id: int, approver: str) -> ScrapRequest:
        request = db.get(ScrapRequest, request_id)
        if not request:
            raise ValueError("scrap request not found")
        asset = db.get(Asset, request.asset_id)
        request.status = "已驳回"
        request.approver = approver
        request.approved_at = datetime.utcnow()
        if asset:
            from_status = asset.status
            asset.status = "idle"
            LifecycleService.record(db, asset.asset_id, "SCRAP_REJECT", from_status, "idle", approver, request.reason)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def generate_no(db: Session) -> str:
        return f"SC-{datetime.utcnow().year}-{db.query(ScrapRequest).count() + 1:04d}"
