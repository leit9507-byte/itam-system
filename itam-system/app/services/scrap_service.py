from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.scrap import ScrapRequest
from app.services.audit_log_service import AuditLogService
from app.services.lifecycle_service import LifecycleService


class ScrapService:
    @staticmethod
    def list_requests(
        db: Session,
        page: int = 1,
        page_size: int = 0,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        user_context: dict | None = None,
    ) -> dict:
        query = db.query(ScrapRequest)
        query = ScrapService.apply_data_scope(query, user_context)
        if status:
            query = query.filter(ScrapRequest.status == status)
        if created_from:
            query = query.filter(ScrapRequest.created_at >= created_from)
        if created_to:
            query = query.filter(ScrapRequest.created_at <= created_to)
        total = query.count()
        query = query.order_by(ScrapRequest.id.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        return {"list": query.all(), "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def apply_data_scope(query, user_context: dict | None):
        if can_view_all_data(user_context):
            return query
        dept_id = scoped_dept_id(user_context)
        identities = scoped_user_identities(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter(ScrapRequest.dept_id == dept_id)
        if identities:
            return query.filter(ScrapRequest.owner_user_id.in_(identities))
        return query.filter(False)

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
        AuditLogService.record_operation(db, "scrap", "create", operator, "scrap_request", request.request_no, f"提交报废申请 {asset.asset_id}", payload)
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
        AuditLogService.record_operation(db, "scrap", "approve", approver, "scrap_request", request.request_no, f"报废审批通过 {request.asset_id}")
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
        AuditLogService.record_operation(db, "scrap", "reject", approver, "scrap_request", request.request_no, f"报废审批驳回 {request.asset_id}")
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def generate_no(db: Session) -> str:
        return f"SC-{datetime.utcnow().year}-{db.query(ScrapRequest).count() + 1:04d}"
