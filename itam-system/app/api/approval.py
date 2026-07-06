import json
import uuid
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.approval import ApprovalInstanceLog, ApprovalRule


router = APIRouter(prefix="/approval", tags=["Approval"])

DEFAULT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
DEFAULT_INSTANCE_URL = "https://open.feishu.cn/open-apis/approval/v4/instances"


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


def config_out(row: ApprovalRule) -> dict:
    return {
        "id": row.id,
        "flow_type": row.flow_type,
        "name": row.name,
        "enabled": row.enabled,
        "min_amount": row.min_amount,
        "max_amount": row.max_amount,
        "dept_id": row.dept_id,
        "provider": row.provider or "feishu",
        "approval_code": row.approval_code,
        "app_id": row.app_id,
        "app_secret": "",
        "app_secret_set": bool(row.app_secret),
        "tenant_access_token_url": row.tenant_access_token_url or DEFAULT_TOKEN_URL,
        "instance_create_url": row.instance_create_url or DEFAULT_INSTANCE_URL,
        "submitter_user_id": row.submitter_user_id,
        "submitter_open_id": row.submitter_open_id,
        "form_template": row.form_template,
        "callback_token": row.callback_token,
        "callback_encrypt_key_set": bool(row.callback_encrypt_key),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def apply_payload(row: ApprovalRule, payload: ApprovalConfigPayload, keep_secret: bool = False) -> None:
    data = payload.model_dump()
    secret = data.pop("app_secret", None)
    data["provider"] = data.get("provider") or "feishu"
    data["tenant_access_token_url"] = data.get("tenant_access_token_url") or DEFAULT_TOKEN_URL
    data["instance_create_url"] = data.get("instance_create_url") or DEFAULT_INSTANCE_URL
    data["level"] = 1
    data["require_all"] = False
    data["approver_role"] = None
    data["approver_user_id"] = None
    for key, value in data.items():
        setattr(row, key, value)
    if secret:
        row.app_secret = secret
    elif not keep_secret:
        row.app_secret = None


@router.get("/configs")
def list_configs(flow_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRule)
    if flow_type:
        query = query.filter(ApprovalRule.flow_type == flow_type)
    rows = query.order_by(ApprovalRule.flow_type.asc(), ApprovalRule.id.asc()).all()
    return [config_out(row) for row in rows]


@router.post("/configs")
def create_config(payload: ApprovalConfigPayload, db: Session = Depends(get_db)):
    row = ApprovalRule(flow_type=payload.flow_type, name=payload.name)
    apply_payload(row, payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return config_out(row)


@router.put("/configs/{config_id}")
def update_config(config_id: int, payload: ApprovalConfigPayload, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval config not found")
    apply_payload(row, payload, keep_secret=True)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return config_out(row)


@router.delete("/configs/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, config_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval config not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/feishu/submit")
def submit_feishu_approval(payload: FeishuSubmitPayload, request: Request, db: Session = Depends(get_db)):
    config = match_config(db, payload.flow_type, payload.amount, payload.dept_id)
    if not config:
        raise HTTPException(status_code=400, detail="未找到启用的飞书审批配置")
    if (config.provider or "feishu") != "feishu":
        raise HTTPException(status_code=400, detail="当前配置不是飞书审批")
    if not config.app_id or not config.app_secret or not config.approval_code:
        raise HTTPException(status_code=400, detail="飞书审批配置缺少 app_id、app_secret 或 approval_code")

    submitter_user_id = payload.user_id or config.submitter_user_id
    submitter_open_id = payload.open_id or config.submitter_open_id
    if not submitter_user_id and not submitter_open_id:
        raise HTTPException(status_code=400, detail="飞书审批需要配置或传入 submitter_user_id/open_id")

    form = build_form(config.form_template, payload.form)
    request_payload = {
        "approval_code": config.approval_code,
        "user_id": submitter_user_id,
        "open_id": submitter_open_id,
        "form": json.dumps(form, ensure_ascii=False),
        "uuid": str(uuid.uuid4()),
    }
    request_payload = {key: value for key, value in request_payload.items() if value not in (None, "")}
    log = ApprovalInstanceLog(
        flow_type=payload.flow_type,
        config_id=config.id,
        business_id=payload.business_id,
        approval_code=config.approval_code,
        requester=operator_from_request(request),
        request_payload=json.dumps(request_payload, ensure_ascii=False),
        status="submitting",
    )
    db.add(log)
    db.flush()
    try:
        token = fetch_tenant_access_token(config)
        response = post_json(config.instance_create_url or DEFAULT_INSTANCE_URL, request_payload, {"Authorization": f"Bearer {token}"})
        log.response_payload = json.dumps(response, ensure_ascii=False)
        log.instance_code = extract_instance_code(response)
        log.status = "submitted" if log.instance_code else "submitted_unknown"
        db.commit()
        db.refresh(log)
        return {"ok": True, "config": config_out(config), "instance": instance_out(log), "feishu": response}
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"飞书审批提交失败：{exc}") from exc


@router.get("/instances")
def list_instances(flow_type: str | None = None, business_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(ApprovalInstanceLog)
    if flow_type:
        query = query.filter(ApprovalInstanceLog.flow_type == flow_type)
    if business_id:
        query = query.filter(ApprovalInstanceLog.business_id == business_id)
    rows = query.order_by(ApprovalInstanceLog.created_at.desc(), ApprovalInstanceLog.id.desc()).limit(min(max(limit, 1), 500)).all()
    return [instance_out(row) for row in rows]


@router.get("/rules")
def list_rules(flow_type: str | None = None, db: Session = Depends(get_db)):
    return list_configs(flow_type, db)


@router.post("/rules")
def create_rule(payload: ApprovalConfigPayload, db: Session = Depends(get_db)):
    return create_config(payload, db)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, payload: ApprovalConfigPayload, db: Session = Depends(get_db)):
    return update_config(rule_id, payload, db)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    return delete_config(rule_id, db)


@router.get("/evaluate")
def evaluate_rules(flow_type: str, amount: float = 0, dept_id: str | None = None, db: Session = Depends(get_db)):
    config = match_config(db, flow_type, amount, dept_id)
    return {"flow_type": flow_type, "amount": amount, "dept_id": dept_id, "config": config_out(config) if config else None}


def match_config(db: Session, flow_type: str, amount: float = 0, dept_id: str | None = None) -> ApprovalRule | None:
    query = db.query(ApprovalRule).filter(ApprovalRule.enabled.is_(True), ApprovalRule.flow_type == flow_type)
    query = query.filter(or_(ApprovalRule.min_amount.is_(None), ApprovalRule.min_amount <= amount))
    query = query.filter(or_(ApprovalRule.max_amount.is_(None), ApprovalRule.max_amount >= amount))
    if dept_id:
        query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == "", ApprovalRule.dept_id == dept_id))
    else:
        query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == ""))
    return query.order_by(ApprovalRule.dept_id.desc(), ApprovalRule.min_amount.desc(), ApprovalRule.id.asc()).first()


def build_form(template_text: str | None, submitted: list[dict] | dict | None) -> list[dict]:
    if submitted:
        return submitted if isinstance(submitted, list) else [{"id": key, "value": value} for key, value in submitted.items()]
    if not template_text:
        return []
    try:
        parsed = json.loads(template_text)
    except json.JSONDecodeError as exc:
        raise ValueError("form_template 必须是 JSON") from exc
    return parsed if isinstance(parsed, list) else [{"id": key, "value": value} for key, value in parsed.items()]


def fetch_tenant_access_token(config: ApprovalRule) -> str:
    response = post_json(
        config.tenant_access_token_url or DEFAULT_TOKEN_URL,
        {"app_id": config.app_id, "app_secret": config.app_secret},
    )
    token = response.get("tenant_access_token") or response.get("data", {}).get("tenant_access_token")
    if not token:
        raise ValueError(response.get("msg") or "tenant_access_token missing")
    return token


def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = UrlRequest(url, data=body, headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            data = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise ValueError(str(exc.reason)) from exc
    result = json.loads(data or "{}")
    code = result.get("code", 0)
    if code not in (0, None):
        raise ValueError(result.get("msg") or data)
    return result


def extract_instance_code(response: dict) -> str | None:
    data = response.get("data") or {}
    return data.get("instance_code") or response.get("instance_code")


def instance_out(row: ApprovalInstanceLog) -> dict:
    return {
        "id": row.id,
        "flow_type": row.flow_type,
        "config_id": row.config_id,
        "business_id": row.business_id,
        "approval_code": row.approval_code,
        "instance_code": row.instance_code,
        "status": row.status,
        "requester": row.requester,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
