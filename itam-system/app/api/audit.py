from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.audit_rule import AuditRule
from app.reports.generator import AuditReportGenerator
from app.services.audit_engine import AuditEngine


router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditRunRequest(BaseModel):
    users: list[dict] = []


class AuditRulePayload(BaseModel):
    rule_code: str
    name: str
    severity: str = "medium"
    enabled: bool = True
    scope_category: str | None = None
    threshold_value: float | None = None
    threshold_days: int | None = None


last_report_path: str | None = None


def default_rules() -> list[dict]:
    settings = get_settings()
    return [
        {
            "rule_code": "USER_ASSET_COUNT_LIMIT",
            "name": "用户资产数量超限",
            "severity": "medium",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.max_assets_per_user),
            "threshold_days": None,
            "description": "按使用人统计名下资产数量，可限定某一设备类型。",
        },
        {
            "rule_code": "ASSET_IDLE_OVER_90_DAYS",
            "name": "资产闲置超期",
            "severity": "low",
            "enabled": True,
            "scope_category": "",
            "threshold_value": None,
            "threshold_days": settings.idle_days_threshold,
            "description": "库存中或闲置资产超过指定天数后命中。",
        },
        {
            "rule_code": "HIGH_VALUE_WITHOUT_DEPT",
            "name": "高价值资产未绑定部门",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold),
            "threshold_days": None,
            "description": "资产原值超过阈值但没有部门归属时命中。",
        },
        {
            "rule_code": "SINGLE_OWNER_VALUE_LIMIT",
            "name": "单人资产价值超标",
            "severity": "high",
            "enabled": True,
            "scope_category": "",
            "threshold_value": float(settings.high_value_threshold * 2),
            "threshold_days": None,
            "description": "按使用人统计名下资产总价值，超过阈值时命中。",
        },
    ]


def serialize_rule(rule: AuditRule, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "name": rule.name,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "scope_category": rule.scope_category or "",
        "threshold_value": rule.threshold_value,
        "threshold_days": rule.threshold_days,
        "description": fallback.get("description", ""),
    }


@router.get("/rules")
def list_audit_rules(db: Session = Depends(get_db)):
    persisted = {item.rule_code: item for item in db.query(AuditRule).all()}
    rows = []
    for item in default_rules():
        saved = persisted.get(item["rule_code"])
        rows.append(serialize_rule(saved, item) if saved else item)
    return rows


@router.post("/rules")
def save_audit_rules(payload: list[AuditRulePayload], db: Session = Depends(get_db)):
    saved_rows = []
    for item in payload:
        rule = db.query(AuditRule).filter(AuditRule.rule_code == item.rule_code).first()
        if not rule:
            rule = AuditRule(rule_code=item.rule_code)
            db.add(rule)
        rule.name = item.name
        rule.severity = item.severity
        rule.enabled = item.enabled
        rule.scope_category = item.scope_category or ""
        rule.threshold_value = item.threshold_value
        rule.threshold_days = item.threshold_days
        saved_rows.append(rule)
    db.commit()
    return list_audit_rules(db)


@router.post("/run")
def run_audit(payload: AuditRunRequest | None = None, db: Session = Depends(get_db)):
    global last_report_path
    result = AuditEngine(db).run(users=payload.users if payload else [])
    last_report_path = AuditReportGenerator().generate(result)
    return result


@router.get("/report")
def get_audit_report(db: Session = Depends(get_db)):
    global last_report_path
    if not last_report_path:
        result = AuditEngine(db).run()
        last_report_path = AuditReportGenerator().generate(result)
    return FileResponse(last_report_path, media_type="text/html", filename="audit_report.html")
