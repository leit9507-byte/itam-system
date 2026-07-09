from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.scrap import ScrapRequest
from app.services.audit_log_service import AuditLogService
from app.services.lifecycle_service import LifecycleService
from app.services.notification_service import NotificationService


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
        LifecycleService.record(
            db,
            asset.asset_id,
            "SCRAP_REQUEST",
            from_status,
            "pending_scrap",
            operator,
            LifecycleService.structured_remark(
                reason=request.reason or "提交报废申请",
                object=f"报废单 {request.request_no}",
                previous_owner=asset.owner_user_id or "-",
                new_owner=request.applicant or "-",
                location=asset.location,
                extra={
                    "disposal_method": request.disposal_method or "",
                    "estimated_residual_value": request.estimated_residual_value or 0,
                },
            ),
        )
        AuditLogService.record_operation(db, "scrap", "create", operator, "scrap_request", request.request_no, f"提交报废申请 {asset.asset_id}", payload)
        db.commit()
        db.refresh(request)
        NotificationService.send_event(
            db,
            "scrap",
            "报废申请已提交",
            [
                f"报废单号：{request.request_no}",
                f"资产编号：{request.asset_id}",
                f"资产名称：{request.asset_name or '-'}",
                f"报废原因：{request.reason or '-'}",
                f"预计残值：￥{request.estimated_residual_value or 0:,.0f}",
            ],
        )
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
            LifecycleService.record(
                db,
                asset.asset_id,
                "SCRAP_APPROVE",
                from_status,
                "scrapped",
                approver,
                LifecycleService.structured_remark(
                    reason=request.reason or "报废审批通过",
                    object=f"报废单 {request.request_no}",
                    previous_owner=asset.owner_user_id or "-",
                    new_owner=approver,
                    location=asset.location,
                    extra={"approved_at": request.approved_at.isoformat() if request.approved_at else ""},
                ),
            )
        AuditLogService.record_operation(db, "scrap", "approve", approver, "scrap_request", request.request_no, f"报废审批通过 {request.asset_id}")
        db.commit()
        db.refresh(request)
        NotificationService.send_event(
            db,
            "scrap",
            "报废审批已通过",
            [
                f"报废单号：{request.request_no}",
                f"资产编号：{request.asset_id}",
                f"资产名称：{request.asset_name or '-'}",
                f"审批人：{approver}",
                f"处理结果：资产已标记为已报废",
            ],
        )
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
            LifecycleService.record(
                db,
                asset.asset_id,
                "SCRAP_REJECT",
                from_status,
                "idle",
                approver,
                LifecycleService.structured_remark(
                    reason=request.reason or "报废审批驳回",
                    object=f"报废单 {request.request_no}",
                    previous_owner=asset.owner_user_id or "-",
                    new_owner=approver,
                    location=asset.location,
                    extra={"approved_at": request.approved_at.isoformat() if request.approved_at else ""},
                ),
            )
        AuditLogService.record_operation(db, "scrap", "reject", approver, "scrap_request", request.request_no, f"报废审批驳回 {request.asset_id}")
        db.commit()
        db.refresh(request)
        NotificationService.send_event(
            db,
            "scrap",
            "报废审批已驳回",
            [
                f"报废单号：{request.request_no}",
                f"资产编号：{request.asset_id}",
                f"资产名称：{request.asset_name or '-'}",
                f"审批人：{approver}",
                f"处理结果：资产恢复为闲置",
            ],
        )
        return request

    @staticmethod
    def dispose(db: Session, request_id: int, payload: dict, operator: str) -> ScrapRequest:
        request = db.get(ScrapRequest, request_id)
        if not request:
            raise ValueError("scrap request not found")
        if request.status not in {"已通过", "已处置"}:
            raise ValueError("只有审批通过的报废单可以确认处置")
        asset = db.get(Asset, request.asset_id)
        if asset and asset.status == "disposed":
            request.status = "已处置"
            db.commit()
            db.refresh(request)
            return request
        if asset and asset.status != "scrapped":
            raise ValueError("资产不是已报废状态，不能确认处置")

        request.status = "已处置"
        request.final_residual_value = float(payload.get("final_residual_value") or request.estimated_residual_value or 0)
        request.disposal_remark = payload.get("disposal_remark") or ""
        request.disposed_by = operator
        request.disposed_at = datetime.utcnow()
        if asset:
            from_status = asset.status
            asset.status = "disposed"
            LifecycleService.record(
                db,
                asset.asset_id,
                "SCRAP_DISPOSE",
                from_status,
                "disposed",
                operator,
                LifecycleService.structured_remark(
                    reason=request.disposal_remark or request.disposal_method or "报废资产已完成处置归档",
                    object=f"报废单 {request.request_no}",
                    previous_owner=asset.owner_user_id or "-",
                    new_owner=operator,
                    location=asset.location,
                    extra={
                        "disposal_method": request.disposal_method or "",
                        "final_residual_value": request.final_residual_value or 0,
                        "disposed_at": request.disposed_at.isoformat() if request.disposed_at else "",
                    },
                ),
            )
        AuditLogService.record_operation(
            db,
            "scrap",
            "dispose",
            operator,
            "scrap_request",
            request.request_no,
            f"确认报废资产处置 {request.asset_id}",
            payload,
        )
        db.commit()
        db.refresh(request)
        NotificationService.send_event(
            db,
            "scrap",
            "报废资产已处置",
            [
                f"报废单号：{request.request_no}",
                f"资产编号：{request.asset_id}",
                f"处置方式：{request.disposal_method or '-'}",
                f"实际残值：¥{request.final_residual_value or 0:,.0f}",
                f"处置人：{operator}",
            ],
        )
        return request

    @staticmethod
    def generate_no(db: Session) -> str:
        return f"SC-{datetime.utcnow().year}-{db.query(ScrapRequest).count() + 1:04d}"
