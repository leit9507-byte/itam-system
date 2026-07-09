from datetime import datetime
from io import StringIO
import csv
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
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
    connection_count = None
    try:
        row = db.execute(text("SHOW STATUS LIKE 'Threads_connected'")).first()
        if row:
            connection_count = int(row[1])
    except Exception:
        connection_count = None
    disk = disk_usage(upload_dir)
    return {
        "service": "itam-system",
        "checked_at": datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
        "database": {"ok": database_ok, "message": database_message, "connections": connection_count},
        "upload_dir": {"path": str(upload_dir), "exists": upload_dir.exists(), "disk": disk},
        "scheduler": {"ldap_sync": "enabled"},
    }


@router.get("/logs")
def operation_logs(page: int = 1, page_size: int = 100, limit: int | None = None, db: Session = Depends(get_db)):
    clean_page = max(page, 1)
    clean_page_size = min(max(limit or page_size, 1), 500)
    query = db.query(OperationAuditLog).order_by(OperationAuditLog.created_at.desc(), OperationAuditLog.id.desc())
    total = query.count()
    rows = query.offset((clean_page - 1) * clean_page_size).limit(clean_page_size).all()
    items = [
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
    return {"list": items, "total": total, "page": clean_page, "page_size": clean_page_size}


@router.get("/logs/export")
def export_operation_logs(limit: int = 5000, db: Session = Depends(get_db)):
    rows = (
        db.query(OperationAuditLog)
        .order_by(OperationAuditLog.created_at.desc(), OperationAuditLog.id.desc())
        .limit(min(max(limit, 1), 20000))
        .all()
    )
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "module", "action", "target_type", "target_id", "operator", "summary", "detail", "created_at"])
    for row in rows:
        writer.writerow([
            row.id,
            row.module,
            row.action,
            row.target_type or "",
            row.target_id or "",
            row.operator,
            row.summary or "",
            row.detail or "",
            row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else "",
        ])
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="operation-audit-logs.csv"'},
    )


@router.get("/jobs")
def scheduled_jobs():
    return [
        {"key": "ldap_sync", "name": "Feishu/LDAP user sync", "schedule": "daily", "status": "enabled"},
        {"key": "audit_report", "name": "audit report", "schedule": "manual/weekly", "status": "planned"},
        {"key": "todo_reminder", "name": "todo reminder", "schedule": "daily", "status": "planned"},
        {"key": "backup", "name": "database and upload backup", "schedule": "script/manual", "status": "available"},
    ]


def disk_usage(path: Path) -> dict:
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
    }
