from __future__ import annotations

from datetime import datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.database import Base, engine
from app.core.schema_compat import ensure_compatible_schema
from app.models.audit_log import OperationAuditLog
from app.models.audit_rule import AuditRule
from app.services.identity_service import IdentityService
from app.services.notification_service import NotificationService
from app.services.repair_service import RepairService


def database_status() -> dict:
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    return {
        "initialized": "user_directory" in tables and "assets" in tables,
        "table_count": len(tables),
        "checked_at": datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
    }


def initialize_database(force: bool = False) -> dict:
    before = database_status()
    if before["initialized"] and not force:
        return {
            **before,
            "ok": True,
            "skipped": True,
            "message": "数据库已初始化，如需补齐种子数据可使用 force=true",
        }

    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema(engine)
    with Session(engine) as db:
        seed_database(db)

    after = database_status()
    return {
        **after,
        "ok": True,
        "skipped": False,
        "message": "数据库初始化完成",
    }


def seed_database(db: Session) -> None:
    IdentityService.ensure_seed(db)
    seed_audit_rules(db)
    NotificationService.get_setting(db)
    RepairService.ensure_fault_types(db)
    seed_product_catalog(db)
    db.add(OperationAuditLog(module="ops", action="init_database", target_type="database", target_id="current", operator="system", summary="初始化数据库基础表和种子数据"))
    db.commit()


def seed_audit_rules(db: Session) -> None:
    from app.api.audit import default_rules

    for item in default_rules():
        rule = db.query(AuditRule).filter(AuditRule.rule_code == item["rule_code"]).first()
        if not rule:
            rule = AuditRule(rule_code=item["rule_code"])
            db.add(rule)
        rule.name = item["name"]
        rule.severity = item["severity"]
        rule.enabled = item["enabled"]
        rule.scope_category = item.get("scope_category") or ""
        rule.threshold_value = item.get("threshold_value")
        rule.threshold_days = item.get("threshold_days")
    db.flush()


def seed_product_catalog(db: Session) -> None:
    from app.api.product import ensure_seed

    ensure_seed(db)
