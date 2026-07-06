from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.approval import ApprovalInstanceLog, ApprovalRule
from app.services.audit_log_service import AuditLogService
from app.services.approval_service import ApprovalService, DEFAULT_INSTANCE_URL, DEFAULT_TOKEN_URL


router = APIRouter(prefix="/approval", tags=["Approval"])


class ApprovalConfigPayload(BaseModel):
    flow_type: str
    name: str
    enabled: bool = True
    min_amount: float | None = None
    max_amount: float | None = None
    dept_id: str | None = None
    provider: str = "feishu"
    approval_code: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    tenant_access_token_url: str | None = DEFAULT_TOKEN_URL
    instance_create_url: str | None = DEFAULT_INSTANCE_URL
    submitter_user_id: str | None = None
    submitter_open_id: str | None = None
    form_template: str | None = None
    callback_token: str | None = None
    callback_encrypt_key: str | None = None


class FeishuSubmitPayload(BaseModel):
    flow_type: str
    business_id: str | None = None
    amount: float = 0
    dept_id: str | None = None
    user_id: str | None = None
    open_id: str | None = None
    form: list[dict] | dict | None = None
    summary: str | None = None


@router.get("/configs")
def list_configs(flow_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRule)
    if flow_type:
        query = query.filter(ApprovalRule.flow_type == flow_type)
    rows = query.order_by(ApprovalRule.flow_type.asc(), ApprovalRule.id.asc()).all()
    return [ApprovalService.config_out(row) for row in rows]


@router.post("/configs")
def create_config(payload: ApprovalConfigPayload, request: Request, db: Session = Depends(get_db)):
    row = ApprovalRule(flow_type=payload.flow_type, name=payload.name)
    ApprovalService.apply_config_payload(row, payload)
    db.add(row)
    AuditLogService.record_operation(db, "approval", "config_create", operator_from_request(request), "approval_config", payload.flow_type, f"创建飞书审批配置 {payload.name}", payload.model_dump(exclude={"app_secret", "callback_encrypt_key"}))
    db.commit()
    db.refresh(row)
    return ApprovalService.config_out(row)


@router.put("/configs/{config_id}")
def update_config(config_id: int, payload: ApprovalConfigPayload, request: Request, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval config not found")
    ApprovalService.apply_config_payload(row, payload, keep_secret=True)
    row.updated_at = datetime.utcnow()
    AuditLogService.record_operation(db, "approval", "config_update", operator_from_request(request), "approval_config", str(row.id), f"更新飞书审批配置 {row.name}", payload.model_dump(exclude={"app_secret", "callback_encrypt_key"}))
    db.commit()
    db.refresh(row)
    return ApprovalService.config_out(row)


@router.delete("/configs/{config_id}")
def delete_config(config_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval config not found")
    AuditLogService.record_operation(db, "approval", "config_delete", operator_from_request(request), "approval_config", str(row.id), f"删除飞书审批配置 {row.name}")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/feishu/submit")
def submit_feishu_approval(payload: FeishuSubmitPayload, request: Request, db: Session = Depends(get_db)):
    try:
        result = ApprovalService.submit_feishu_approval(
            db,
            payload.flow_type,
            payload.business_id,
            payload.amount,
            payload.dept_id,
            payload.user_id,
            payload.open_id,
            payload.form,
            operator_from_request(request),
        )
        return {
            "ok": True,
            "config": ApprovalService.config_out(result["config"]),
            "instance": ApprovalService.instance_out(result["instance"]),
            "feishu": result["feishu"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"飞书审批提交失败：{exc}") from exc


@router.post("/feishu/callback")
async def feishu_callback(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    try:
        return ApprovalService.handle_feishu_callback(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/instances")
def list_instances(flow_type: str | None = None, business_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(ApprovalInstanceLog)
    if flow_type:
        query = query.filter(ApprovalInstanceLog.flow_type == flow_type)
    if business_id:
        query = query.filter(ApprovalInstanceLog.business_id == business_id)
    rows = query.order_by(ApprovalInstanceLog.created_at.desc(), ApprovalInstanceLog.id.desc()).limit(min(max(limit, 1), 500)).all()
    return [ApprovalService.instance_out(row) for row in rows]


@router.get("/rules")
def list_rules(flow_type: str | None = None, db: Session = Depends(get_db)):
    return list_configs(flow_type, db)


@router.post("/rules")
def create_rule(payload: ApprovalConfigPayload, request: Request, db: Session = Depends(get_db)):
    return create_config(payload, request, db)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, payload: ApprovalConfigPayload, request: Request, db: Session = Depends(get_db)):
    return update_config(rule_id, payload, request, db)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, request: Request, db: Session = Depends(get_db)):
    return delete_config(rule_id, request, db)


@router.get("/evaluate")
def evaluate_rules(flow_type: str, amount: float = 0, dept_id: str | None = None, db: Session = Depends(get_db)):
    config = ApprovalService.match_config(db, flow_type, amount, dept_id)
    return {"flow_type": flow_type, "amount": amount, "dept_id": dept_id, "config": ApprovalService.config_out(config) if config else None}
