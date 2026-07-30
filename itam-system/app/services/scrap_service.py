from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.time import app_now, utc_now
from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.scrap import ScrapRequest
from app.models.user import UserDirectory
from app.services.audit_log_service import AuditLogService
from app.services.asset_service import AssetService
from app.services.asset_residual_service import AssetResidualService
from app.services.lifecycle_service import LifecycleService
from app.services.notification_service import NotificationService
from app.services.number_service import NumberService


class ScrapService:
    DISPOSAL_METHODS = {"报废", "变卖", "员工领用"}

    @staticmethod
    def normalize_disposal_method(value: str | None) -> str:
        method = (value or "").strip()
        aliases = {
            "环保回收": "报废",
            "供应商回收": "报废",
            "内部拆件": "报废",
            "销毁处理": "报废",
            "Recycle": "报废",
            "出售": "变卖",
            "转卖": "变卖",
        }
        method = aliases.get(method, method)
        return method if method in ScrapService.DISPOSAL_METHODS else ""

    @staticmethod
    def list_requests(
        db: Session,
        page: int = 1,
        page_size: int = 0,
        status: str | None = None,
        asset_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        user_context: dict | None = None,
        disposal_method: str | None = None,
    ) -> dict:
        query = db.query(ScrapRequest)
        query = ScrapService.apply_data_scope(query, user_context)
        if status:
            query = query.filter(ScrapRequest.status == status)
        if asset_id:
            query = query.filter(ScrapRequest.asset_id == asset_id)
        if disposal_method:
            normalized_method = ScrapService.normalize_disposal_method(disposal_method)
            query = query.filter(ScrapRequest.disposal_method == normalized_method) if normalized_method else query.filter(False)
        if created_from:
            query = query.filter(ScrapRequest.created_at >= created_from)
        if created_to:
            query = query.filter(ScrapRequest.created_at <= created_to)
        total = query.count()
        query = query.order_by(ScrapRequest.id.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        rows = query.all()
        asset_ids = [row.asset_id for row in rows if row.asset_id]
        assets = {asset.asset_id: asset for asset in db.query(Asset).filter(Asset.asset_id.in_(asset_ids)).all()} if asset_ids else {}
        for row in rows:
            asset = assets.get(row.asset_id)
            row.asset_no = asset.asset_no if asset else row.asset_id
            row.registration_no = row.request_no
            row.flow_no = row.retirement_flow_no or row.request_no
        return {"list": rows, "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def list_flows(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        asset_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        user_context: dict | None = None,
        disposal_method: str | None = None,
    ) -> dict:
        result = ScrapService.list_requests(
            db,
            page=1,
            page_size=0,
            status=status,
            asset_id=asset_id,
            created_from=created_from,
            created_to=created_to,
            user_context=user_context,
            disposal_method=disposal_method,
        )
        groups: dict[str, list[ScrapRequest]] = {}
        for row in result["list"]:
            groups.setdefault(row.retirement_flow_no or row.request_no, []).append(row)

        flows = [ScrapService.flow_row(flow_no, rows) for flow_no, rows in groups.items()]
        flows.sort(key=lambda item: item["sort_id"], reverse=True)
        total = len(flows)
        clean_page = max(page, 1)
        if page_size and page_size > 0:
            start = (clean_page - 1) * page_size
            flows = flows[start : start + page_size]
        return {"list": flows, "total": total, "page": clean_page, "page_size": page_size or total}

    @staticmethod
    def flow_row(flow_no: str, rows: list[ScrapRequest]) -> dict:
        rows = sorted(rows, key=lambda item: item.id or 0, reverse=True)
        first = rows[0]
        unique_statuses = {row.status for row in rows if row.status}
        unique_methods = {row.disposal_method for row in rows if row.disposal_method}
        unique_companies = {row.company for row in rows if row.company}
        item_dicts = [ScrapService.request_row(row) for row in rows]
        return {
            "id": flow_no,
            "flow_no": flow_no,
            "retirement_flow_no": first.retirement_flow_no or "",
            "registration_no": first.request_no,
            "request_no": flow_no,
            "company": next(iter(unique_companies), "") if len(unique_companies) <= 1 else "多公司",
            "quantity": len(rows),
            "asset_summary": "，".join([f"{row.asset_name or row.asset_id}({row.asset_no or row.asset_id})" for row in rows[:3]]) + ("…" if len(rows) > 3 else ""),
            "status": next(iter(unique_statuses), "") if len(unique_statuses) <= 1 else "混合",
            "disposal_method": next(iter(unique_methods), "") if len(unique_methods) <= 1 else "混合",
            "retirement_date": first.retirement_date,
            "retirement_approval_no": first.retirement_approval_no or "",
            "dispose_recipient_user_id": first.dispose_recipient_user_id or "",
            "dispose_recipient_name": first.dispose_recipient_name or "",
            "disposal_remark": first.disposal_remark or "",
            "estimated_residual_value": sum(float(row.estimated_residual_value or 0) for row in rows),
            "final_residual_value": sum(float(row.final_residual_value or 0) for row in rows),
            "created_at": first.created_at,
            "disposed_at": first.disposed_at,
            "disposed_by": first.disposed_by or "",
            "items": item_dicts,
            "sort_id": max(row.id or 0 for row in rows),
        }

    @staticmethod
    def request_row(row: ScrapRequest) -> dict:
        return {
            "id": row.id,
            "request_no": row.request_no,
            "registration_no": row.request_no,
            "retirement_flow_no": row.retirement_flow_no or "",
            "flow_no": row.retirement_flow_no or row.request_no,
            "asset_id": row.asset_id,
            "asset_no": getattr(row, "asset_no", "") or row.asset_id,
            "asset_name": row.asset_name,
            "asset_sn": row.asset_sn,
            "company": row.company,
            "category": row.category,
            "brand": row.brand,
            "model": row.model,
            "owner_user_id": row.owner_user_id,
            "dept_id": row.dept_id,
            "location": row.location,
            "purchase_price": row.purchase_price or 0,
            "purchase_date": row.purchase_date,
            "purchase_approval_no": row.purchase_approval_no,
            "purchase_supplier_name": row.purchase_supplier_name,
            "applicant": row.applicant,
            "reason": row.reason,
            "disposal_method": row.disposal_method,
            "retirement_date": row.retirement_date,
            "retirement_approval_no": row.retirement_approval_no,
            "estimated_residual_value": row.estimated_residual_value or 0,
            "final_residual_value": row.final_residual_value or 0,
            "disposal_remark": row.disposal_remark,
            "dispose_recipient_user_id": row.dispose_recipient_user_id,
            "dispose_recipient_name": row.dispose_recipient_name,
            "disposed_by": row.disposed_by,
            "disposed_at": row.disposed_at,
            "status": row.status,
            "approver": row.approver,
            "approved_at": row.approved_at,
            "created_at": row.created_at,
        }

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
    def create_request(db: Session, asset_id: str, payload: dict, operator: str = "资产管理员", user_context: dict | None = None) -> ScrapRequest:
        asset = AssetService.get_scoped_asset(db, asset_id, user_context)
        existed = db.query(ScrapRequest).filter(ScrapRequest.asset_id == asset_id, ScrapRequest.status.in_(["待处置", "审批中", "已通过"])).first()
        if existed:
            retirement_flow_no = (payload.get("retirement_flow_no") or "").strip()
            if retirement_flow_no and not existed.retirement_flow_no:
                existed.retirement_flow_no = retirement_flow_no
                db.commit()
                db.refresh(existed)
            return existed
        request = ScrapRequest(
            request_no=ScrapService.generate_no(db),
            retirement_flow_no=(payload.get("retirement_flow_no") or "").strip() or None,
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
            disposal_method=None,
            retirement_date=payload.get("retirement_date"),
            retirement_approval_no=payload.get("retirement_approval_no") or "",
            estimated_residual_value=AssetResidualService.calculate_asset(asset, db=db),
            status="待处置",
        )
        from_status = asset.status
        AssetService.validate_transition(from_status, "pending_scrap")
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
                reason=request.reason or "提交报废处置登记",
                object=f"报废单 {request.request_no}",
                previous_owner=asset.owner_user_id or "-",
                new_owner=request.applicant or "-",
                location=asset.location,
                extra={
                    "retirement_flow_no": request.retirement_flow_no or request.request_no,
                    "retirement_date": request.retirement_date.isoformat() if request.retirement_date else "",
                    "retirement_approval_no": request.retirement_approval_no or "",
                    "estimated_residual_value": request.estimated_residual_value or 0,
                },
            ),
        )
        AuditLogService.record_operation(db, "scrap", "create", operator, "scrap_request", request.request_no, f"登记报废处置 {asset.asset_id}", payload)
        db.commit()
        db.refresh(request)
        NotificationService.send_event(
            db,
            "scrap",
            "报废处置待登记",
            [
                f"报废单号：{request.request_no}",
                f"资产编号：{request.asset_id}",
                f"资产名称：{request.asset_name or '-'}",
                f"报废原因：{request.reason or '-'}",
                f"退役审批单号：{request.retirement_approval_no or '-'}",
                f"预计残值：￥{request.estimated_residual_value or 0:,.0f}",
            ],
        )
        return request

    @staticmethod
    def dispose(db: Session, request_id: int, payload: dict, operator: str, user_context: dict | None = None) -> ScrapRequest:
        request = ScrapService.apply_data_scope(
            db.query(ScrapRequest).filter(ScrapRequest.id == request_id), user_context
        ).first()
        if not request:
            raise ValueError("scrap request not found")
        if request.status not in {"待处置", "审批中", "已通过", "已处置"}:
            raise ValueError("只有待处置的报废单可以登记处置")
        asset = AssetService.get_scoped_asset(db, request.asset_id, user_context)
        if asset and asset.status == "disposed":
            request.status = "已处置"
            asset.status = "scrapped"
            db.commit()
            db.refresh(request)
            return request
        if asset and asset.status not in {"pending_scrap", "scrapped", "ready_scrap"}:
            raise ValueError("资产不是待报废或已报废状态，不能登记处置")

        disposal_method = ScrapService.normalize_disposal_method(payload.get("disposal_method"))
        if not disposal_method:
            raise ValueError("请选择实际处置方式：报废、变卖或员工领用")
        retirement_approval_no = (payload.get("retirement_approval_no") or "").strip()
        if not retirement_approval_no:
            raise ValueError("请填写退役审批单号")
        retirement_flow_no = (payload.get("retirement_flow_no") or "").strip()
        disposal_remark = (payload.get("disposal_remark") or "").strip()
        recipient_user_id = (payload.get("dispose_recipient_user_id") or "").strip()
        recipient_name = (payload.get("dispose_recipient_name") or "").strip()
        if disposal_method == "员工领用":
            user = None
            if recipient_user_id:
                user = (
                    db.query(UserDirectory)
                    .filter(or_(UserDirectory.user_id == recipient_user_id, UserDirectory.username == recipient_user_id))
                    .first()
                )
            if user:
                recipient_user_id = user.user_id
                recipient_name = user.display_name or user.username or recipient_name
            if not recipient_user_id and not recipient_name:
                raise ValueError("员工领用处置必须选择领用员工")
        elif disposal_method == "变卖":
            recipient_user_id = ""
        else:
            recipient_user_id = ""
            recipient_name = ""

        request.status = "已处置"
        request.disposal_method = disposal_method
        request.retirement_date = payload.get("retirement_date") or request.retirement_date or utc_now()
        request.retirement_approval_no = retirement_approval_no
        request.retirement_flow_no = retirement_flow_no or request.retirement_flow_no or request.request_no
        final_residual_value = payload.get("final_residual_value")
        request.final_residual_value = float(
            request.estimated_residual_value or 0 if final_residual_value is None else final_residual_value
        )
        request.disposal_remark = disposal_remark
        request.dispose_recipient_user_id = recipient_user_id or None
        request.dispose_recipient_name = recipient_name or None
        request.disposed_by = operator
        request.disposed_at = utc_now()
        if asset:
            from_status = asset.status
            if from_status != "scrapped":
                AssetService.validate_transition(from_status, "scrapped")
            asset.status = "scrapped"
            recipient_label = request.dispose_recipient_name or request.dispose_recipient_user_id or "-"
            dispose_reason = request.disposal_remark or request.disposal_method or "报废资产已完成处置归档"
            if request.disposal_method == "员工领用":
                dispose_reason = request.disposal_remark or f"报废领走：{recipient_label}"
            LifecycleService.record(
                db,
                asset.asset_id,
                "SCRAP_DISPOSE",
                from_status,
                "scrapped",
                operator,
                LifecycleService.structured_remark(
                    reason=dispose_reason,
                    object=f"报废单 {request.request_no}",
                    previous_owner=asset.owner_user_id or "-",
                    new_owner=recipient_label if request.disposal_method in {"员工领用", "变卖"} else operator,
                    location=asset.location,
                    extra={
                        "retirement_flow_no": request.retirement_flow_no or request.request_no,
                        "disposal_method": request.disposal_method or "",
                        "retirement_date": request.retirement_date.isoformat() if request.retirement_date else "",
                        "retirement_approval_no": request.retirement_approval_no or "",
                        "dispose_recipient_user_id": request.dispose_recipient_user_id or "",
                        "dispose_recipient_name": request.dispose_recipient_name or "",
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
                f"退役时间：{request.retirement_date.date().isoformat() if request.retirement_date else '-'}",
                f"退役审批单号：{request.retirement_approval_no or '-'}",
                f"处置方式：{request.disposal_method or '-'}",
                f"处置接收方：{request.dispose_recipient_name or request.dispose_recipient_user_id or '-'}",
                f"实际残值：¥{request.final_residual_value or 0:,.0f}",
                f"处置人：{operator}",
            ],
        )
        return request

    @staticmethod
    def generate_no(db: Session) -> str:
        year = app_now().year
        return NumberService.next(db, f"scrap:{year}", f"SC-{year}-", 4)

    @staticmethod
    def generate_retirement_flow_no(db: Session) -> str:
        year = app_now().year
        return NumberService.next(db, f"retirement_flow:{year}", f"RT-{year}-", 4)
