from datetime import datetime
import hmac
from io import StringIO
import csv
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_log import OperationAuditLog
from app.services.database_init_service import database_status, initialize_database
from app.services.database_config_service import current_database_config, save_database_config, test_database_config


router = APIRouter(prefix="/ops", tags=["Operations"])


class DatabaseConfigPayload(BaseModel):
    host: str
    port: int = 3306
    database: str
    username: str
    password: str = ""
    charset: str = "utf8mb4"
    timezone: str = "+08:00"
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 1800
    pool_timeout: int = 30
    connect_timeout: int = 10


class DatabaseInitPayload(BaseModel):
    force: bool = False


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


def apply_log_filters(
    query,
    module: str | None = None,
    action: str | None = None,
    operator: str | None = None,
    keyword: str | None = None,
    start: str | None = None,
    end: str | None = None,
):
    if module:
        query = query.filter(OperationAuditLog.module == module)
    if action:
        query = query.filter(OperationAuditLog.action == action)
    if operator:
        query = query.filter(OperationAuditLog.operator.like(f"%{operator.strip()}%"))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                OperationAuditLog.target_type.like(pattern),
                OperationAuditLog.target_id.like(pattern),
                OperationAuditLog.summary.like(pattern),
                OperationAuditLog.detail.like(pattern),
            )
        )
    if start:
        query = query.filter(OperationAuditLog.created_at >= parse_log_datetime(start, datetime.min.time()))
    if end:
        query = query.filter(OperationAuditLog.created_at <= parse_log_datetime(end, datetime.max.time()))
    return query


@router.get("/logs")
def operation_logs(
    page: int = 1,
    page_size: int = 100,
    limit: int | None = None,
    module: str | None = None,
    action: str | None = None,
    operator: str | None = None,
    keyword: str | None = None,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
):
    clean_page = max(page, 1)
    clean_page_size = min(max(limit or page_size, 1), 500)
    base_query = db.query(OperationAuditLog)
    query = apply_log_filters(base_query, module, action, operator, keyword, start, end)
    query = query.order_by(OperationAuditLog.created_at.desc(), OperationAuditLog.id.desc())
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
            "detail": row.detail,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"list": items, "total": total, "page": clean_page, "page_size": clean_page_size}


@router.get("/error-logs")
def error_logs(
    page: int = 1,
    page_size: int = 100,
    keyword: str | None = None,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
):
    clean_page = max(page, 1)
    clean_page_size = min(max(page_size, 1), 500)
    error_terms = ["%error%", "%fail%", "%exception%", "%错误%", "%失败%", "%异常%"]
    error_filter = or_(
        *[OperationAuditLog.action.like(term) for term in error_terms],
        *[OperationAuditLog.summary.like(term) for term in error_terms],
        *[OperationAuditLog.detail.like(term) for term in error_terms],
    )
    query = db.query(OperationAuditLog).filter(error_filter)
    query = apply_log_filters(query, keyword=keyword, start=start, end=end)
    query = query.order_by(OperationAuditLog.created_at.desc(), OperationAuditLog.id.desc())
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
            "detail": row.detail,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"list": items, "total": total, "page": clean_page, "page_size": clean_page_size}


@router.get("/logs/export")
def export_operation_logs(
    limit: int = 5000,
    module: str | None = None,
    action: str | None = None,
    operator: str | None = None,
    keyword: str | None = None,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
):
    rows = (
        apply_log_filters(db.query(OperationAuditLog), module, action, operator, keyword, start, end)
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


def parse_log_datetime(value: str, fallback_time) -> datetime:
    clean = (value or "").strip()
    if not clean:
        return datetime.combine(datetime.utcnow().date(), fallback_time)
    if len(clean) == 10:
        return datetime.combine(datetime.fromisoformat(clean).date(), fallback_time)
    return datetime.fromisoformat(clean.replace("Z", "+00:00")).replace(tzinfo=None)


@router.get("/jobs")
def scheduled_jobs():
    return [
        {"key": "ldap_sync", "name": "Feishu/LDAP user sync", "schedule": "daily", "status": "enabled"},
        {"key": "audit_report", "name": "audit report", "schedule": "manual/weekly", "status": "planned"},
        {"key": "todo_reminder", "name": "todo reminder", "schedule": "daily", "status": "planned"},
        {"key": "backup", "name": "database and upload backup", "schedule": "script/manual", "status": "available"},
    ]


@router.get("/database-config")
def get_database_config():
    return current_database_config()


@router.post("/database-config/test")
def test_database(payload: DatabaseConfigPayload):
    try:
        return test_database_config(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/database-config")
def update_database_config(payload: DatabaseConfigPayload, db: Session = Depends(get_db)):
    data = payload.model_dump()
    test_result = test_database_config(data)
    if not test_result.get("ok"):
        raise HTTPException(status_code=400, detail=f"数据库连接失败：{test_result.get('message')}")
    try:
        result = save_database_config(data)
        db.add(OperationAuditLog(module="ops", action="update_database_config", target_type="database", target_id=payload.host, operator="system", summary="更新数据库连接配置，等待重启生效"))
        db.commit()
        return {**result, "test": test_result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/database-status")
def get_database_status():
    return database_status()


@router.post("/init-database")
def init_database(payload: DatabaseInitPayload | None = None, x_init_token: str | None = Header(default=None)):
    validate_init_token(x_init_token)
    try:
        return initialize_database(force=bool(payload and payload.force))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def validate_init_token(token: str | None) -> None:
    settings = get_settings()
    expected = settings.init_database_token
    if settings.production_mode and not expected:
        raise HTTPException(status_code=403, detail="生产环境必须配置 INIT_DATABASE_TOKEN 后才能初始化数据库")
    if expected and not hmac.compare_digest(token or "", expected):
        raise HTTPException(status_code=403, detail="初始化令牌不正确")
    if not expected and not settings.production_mode:
        return


def disk_usage(path: Path) -> dict:
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
    }
