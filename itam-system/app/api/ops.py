from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_log import OperationAuditLog


router = APIRouter(prefix="/ops", tags=["Operations"])


@router.get("/health")
def ops_health(db: Session = Depends(get_db)):
    database_ok = True
    database_message = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        database_message = str(exc)
    upload_dir = Path(get_settings().upload_dir)
    return {
        "service": "itam-system",
        "checked_at": datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
        "database": {"ok": database_ok, "message": database_message},
        "upload_dir": {"path": str(upload_dir), "exists": upload_dir.exists()},
        "scheduler": {"ldap_sync": "enabled"},
    }


@router.get("/logs")
def operation_logs(limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(OperationAuditLog)
        .order_by(OperationAuditLog.created_at.desc(), OperationAuditLog.id.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [
        {
            "id": row.id,
            "module": row.module,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "operator": row.operator,
            "summary": row.summary,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/jobs")
def scheduled_jobs():
    return [
        {"key": "ldap_sync", "name": "Feishu/LDAP user sync", "schedule": "daily", "status": "enabled"},
        {"key": "audit_report", "name": "audit report", "schedule": "manual/weekly", "status": "planned"},
        {"key": "todo_reminder", "name": "todo reminder", "schedule": "daily", "status": "planned"},
        {"key": "backup", "name": "database and upload backup", "schedule": "script/manual", "status": "available"},
    ]
