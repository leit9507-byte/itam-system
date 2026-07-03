from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_response import AuditResponse
from app.models.audit_rule import AuditRule
from app.reports.generator import AuditReportGenerator
from app.services.audit_engine import AuditEngine
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditRunRequest(BaseModel):
    users: list[dict] = []
    notify: bool = False


class AuditRulePayload(BaseModel):
    rule_code: str
    name: str
    severity: str = "medium"
    enabled: bool = True
    scope_category: str | None = None
    threshold_value: float | None = None
    threshold_days: int | None = None


class AuditResponsePayload(BaseModel):
    violation_key: str
    asset_id: str | None = None
    rule_code: str
    audit_scope: str = "asset"
    decision: str = "pending"
    reason: str | None = None
    responder: str | None = None


last_report_path: str | None = None


def default_rules() -> list[dict]:
    settings = get_settings()
    return [
        {
            "rule_code": "USER_ASSET_COUNT_LIMIT",
            "name": "人员资产数量超配",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.max_assets_per_user),
            "threshold_days": None,
            "audit_scope": "person",
            "description": "按责任人统计名下资产数量，可限定某一设备类型。",
        },
        {
            "rule_code": "OFFBOARDING_ASSET_NOT_RETURNED",
            "name": "离职人员资产未回收",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": None,
            "audit_scope": "person",
            "description": "责任人已离职、停用或禁用，但资产仍在用、借出或出库时命中。",
        },
        {
            "rule_code": "BORROWED_ASSET_NOT_RETURNED",
            "name": "借用资产超期未回收",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": 30,
            "audit_scope": "person",
            "description": "资产处于借出状态超过指定天数仍未回收时命中。",
        },
        {
            "rule_code": "SINGLE_OWNER_VALUE_LIMIT",
            "name": "人员名下资产价值超标",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold * 2),
            "threshold_days": None,
            "audit_scope": "person",
            "description": "按责任人统计名下资产总价值，超过阈值时命中。",
        },
        {
            "rule_code": "HIGH_VALUE_PURCHASE",
            "name": "超价值采购",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold),
            "threshold_days": None,
            "audit_scope": "asset",
            "description": "资产采购原值超过规则阈值时命中，用于复核审批和采购合理性。",
        },
        {
            "rule_code": "ASSET_IDLE_OVER_90_DAYS",
            "name": "长期闲置",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": settings.idle_days_threshold,
            "audit_scope": "asset",
            "description": "库存中或闲置资产超过指定天数后命中。",
        },
    ]


def serialize_rule(rule: AuditRule, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "name": rule.name or fallback.get("name") or rule.rule_code,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "scope_category": rule.scope_category or "",
        "threshold_value": rule.threshold_value,
        "threshold_days": rule.threshold_days,
        "audit_scope": fallback.get("audit_scope") or infer_rule_scope(rule.rule_code),
        "description": fallback.get("description", ""),
    }


def infer_rule_scope(rule_code: str) -> str:
    if rule_code.startswith("CUSTOM_PERSON_COUNT_"):
        return "person"
    defaults = {item["rule_code"]: item for item in default_rules()}
    return defaults.get(rule_code, {}).get("audit_scope", "asset")


def custom_rule_fallback(rule: AuditRule) -> dict:
    if rule.rule_code.startswith("CUSTOM_PERSON_COUNT_"):
        return {
            "audit_scope": "person",
            "description": "按责任人统计全部设备类型或多个指定设备类型的资产数量，超过阈值时命中。",
        }
    return {"audit_scope": infer_rule_scope(rule.rule_code)}


def serialize_response(row: AuditResponse) -> dict:
    return {
        "id": row.id,
        "violation_key": row.violation_key,
        "asset_id": row.asset_id,
        "rule_code": row.rule_code,
        "audit_scope": row.audit_scope,
        "decision": row.decision,
        "reason": row.reason or "",
        "responder": row.responder or "",
        "updated_at": row.updated_at,
        "created_at": row.created_at,
    }


@router.get("/rules")
def list_audit_rules(db: Session = Depends(get_db)):
    persisted = {item.rule_code: item for item in db.query(AuditRule).all()}
    rows = []
    changed = False
    for item in default_rules():
        saved = persisted.get(item["rule_code"])
        if saved:
            if saved.name != item["name"]:
                saved.name = item["name"]
                changed = True
            rows.append(serialize_rule(saved, item))
        else:
            rows.append(item)
    default_codes = {item["rule_code"] for item in default_rules()}
    custom_rows = [
        serialize_rule(item, custom_rule_fallback(item))
        for item in persisted.values()
        if item.rule_code not in default_codes
    ]
    rows.extend(sorted(custom_rows, key=lambda item: item["id"] or 0))
    if changed:
        db.commit()
    return rows


@router.post("/rules")
def save_audit_rules(payload: list[AuditRulePayload], db: Session = Depends(get_db)):
    defaults = {item["rule_code"]: item for item in default_rules()}
    for item in payload:
        rule = db.query(AuditRule).filter(AuditRule.rule_code == item.rule_code).first()
        if not rule:
            rule = AuditRule(rule_code=item.rule_code)
            db.add(rule)
        rule.name = defaults.get(item.rule_code, {}).get("name", item.name)
        rule.severity = item.severity
        rule.enabled = item.enabled
        rule.scope_category = item.scope_category or ""
        rule.threshold_value = item.threshold_value
        rule.threshold_days = item.threshold_days
    db.commit()
    return list_audit_rules(db)


@router.get("/responses")
def list_audit_responses(db: Session = Depends(get_db)):
    rows = db.query(AuditResponse).order_by(AuditResponse.updated_at.desc()).all()
    return [serialize_response(row) for row in rows]


@router.post("/responses")
def save_audit_response(payload: AuditResponsePayload, db: Session = Depends(get_db)):
    row = db.query(AuditResponse).filter(AuditResponse.violation_key == payload.violation_key).first()
    if not row:
        row = AuditResponse(violation_key=payload.violation_key)
        db.add(row)
    row.asset_id = payload.asset_id
    row.rule_code = payload.rule_code
    row.audit_scope = payload.audit_scope
    row.decision = payload.decision
    row.reason = payload.reason or ""
    row.responder = payload.responder or ""
    db.commit()
    db.refresh(row)
    return serialize_response(row)


@router.post("/run")
def run_audit(payload: AuditRunRequest | None = None, db: Session = Depends(get_db)):
    global last_report_path
    result = AuditEngine(db).run(users=payload.users if payload else [])
    last_report_path = AuditReportGenerator().generate(result)
    violations = result.get("violations") or []
    if payload and payload.notify and violations:
        summary = result.get("audit_summary") or {}
        NotificationService.send_event(
            db,
            "risk",
            "审计发现风险",
            [
                f"风险总数：{len(violations)} 条",
                f"风险评分：{result.get('risk_score', 0)}",
                f"人员风险：{summary.get('person', 0)} 条",
                f"资产风险：{summary.get('asset', 0)} 条",
                f"高风险：{len([item for item in violations if item.get('severity') == 'high'])} 条",
                "处理建议：请进入审计中心查看明细并分派整改",
                f"审计时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            ],
        )
    return result


@router.get("/report")
def get_audit_report(db: Session = Depends(get_db)):
    global last_report_path
    if not last_report_path:
        result = AuditEngine(db).run()
        last_report_path = AuditReportGenerator().generate(result)
    return FileResponse(last_report_path, media_type="text/html", filename="audit_report.html")
