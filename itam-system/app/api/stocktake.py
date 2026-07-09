from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.asset import Asset
from app.models.stocktake import StocktakeItem, StocktakeScanLog, StocktakeTask
from app.services.audit_log_service import AuditLogService
from app.services.asset_service import AssetService
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/stocktake", tags=["Stocktake"])


class StocktakeTaskCreate(BaseModel):
    name: str
    scope: str = "全部"
    target: str | None = None
    targets: list[str] = Field(default_factory=list)
    owner: str | None = None
    include_scrapped: bool = False
    include_disposed: bool = False


class StocktakeItemSubmit(BaseModel):
    actual_location: str | None = None
    result: str = "正常"
    checker: str | None = None
    remark: str | None = None
    scan_raw: str | None = None
    parsed_code: str | None = None
    client_source: str | None = None


class StocktakeExceptionSubmit(BaseModel):
    actual_location: str | None = None
    result: str = "位置不符"
    reporter: str | None = None
    remark: str | None = None
    scan_raw: str | None = None
    parsed_code: str | None = None
    client_source: str | None = None


class StocktakeReviewSubmit(BaseModel):
    review_status: str = "已确认"
    reviewer: str | None = None
    review_note: str | None = None


@router.get("/tasks")
def list_tasks(request: Request, db: Session = Depends(get_db)):
    visible_asset_ids = visible_asset_id_set(db, request)
    tasks = (
        db.query(StocktakeTask)
        .options(joinedload(StocktakeTask.items))
        .order_by(StocktakeTask.created_at.desc())
        .all()
    )
    return [row for row in [serialize_task(task, visible_asset_ids) for task in tasks] if row["total"] > 0]


@router.post("/tasks")
def create_task(payload: StocktakeTaskCreate, request: Request, db: Session = Depends(get_db)):
    task_id = f"ST-{datetime.utcnow().year}-{db.query(StocktakeTask).count() + 1:03d}"
    targets = normalize_targets(payload.target, payload.targets)
    task = StocktakeTask(
        id=task_id,
        name=payload.name,
        scope=payload.scope,
        target="、".join(targets),
        owner=payload.owner or "资产管理员",
        status="待开始",
    )
    for asset in scoped_assets(db, payload.scope, targets, user_context_from_request(request), payload.include_scrapped, payload.include_disposed):
        task.items.append(
            StocktakeItem(
                asset_id=asset.asset_id,
                name=asset.name,
                sn=asset.sn,
                book_location=asset.location or "",
                book_status=asset.status,
                result="未盘",
            )
        )
    db.add(task)
    AuditLogService.record_operation(db, "stocktake", "create_task", operator_from_request(request), "stocktake_task", task.id, f"创建盘点任务 {task.id}", payload.model_dump())
    db.commit()
    db.refresh(task)
    return serialize_task(task, visible_asset_id_set(db, request))


@router.post("/tasks/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task.status == "待开始":
        task.status = "进行中"
        db.commit()
        db.refresh(task)
        NotificationService.send_event(
            db,
            "stocktake",
            "盘点任务已开始",
            [
                f"任务名称：{task.name}",
                f"任务编号：{task.id}",
                f"盘点范围：{task.scope} / {task.target or '全部'}",
                f"应盘资产：{len(task.items)} 台",
                f"负责人：{task.owner or '-'}",
                f"开始时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            ],
        )
    return serialize_task(task)


@router.post("/tasks/{task_id}/items/{asset_id}")
def submit_item(task_id: str, asset_id: str, payload: StocktakeItemSubmit, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    item = next((row for row in task.items if row.asset_id == asset_id or row.sn == asset_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    if task.status == "待开始":
        task.status = "进行中"
    item.actual_location = payload.actual_location or ""
    item.result = payload.result
    item.checker = payload.checker or task.owner
    item.checked_at = datetime.utcnow()
    item.remark = payload.remark or ""
    item.review_status = "无需复核" if item.result == "正常" else "待复核"
    record_scan_log(db, task.id, item.asset_id, payload.scan_raw, payload.parsed_code or asset_id, item.result, payload.client_source, item.checker, "扫码登记")
    AuditLogService.record_operation(db, "stocktake", "scan_submit", item.checker or "system", "stocktake_item", item.asset_id, f"{task.id} 扫码登记 {item.asset_id}")
    refresh_task_status(task)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/items/{asset_id}/exception")
def report_exception(task_id: str, asset_id: str, payload: StocktakeExceptionSubmit, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    item = next((row for row in task.items if row.asset_id == asset_id or row.sn == asset_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    if task.status == "待开始":
        task.status = "进行中"
    item.actual_location = payload.actual_location or ""
    item.result = payload.result if payload.result in {"盘盈", "盘亏", "位置不符", "状态不符"} else "位置不符"
    item.checker = payload.reporter or task.owner
    item.checked_at = datetime.utcnow()
    item.remark = payload.remark or "异常上报，等待复核"
    item.review_status = "待复核"
    item.review_note = ""
    item.reviewed_by = ""
    item.reviewed_at = None
    record_scan_log(db, task.id, item.asset_id, payload.scan_raw, payload.parsed_code or asset_id, item.result, payload.client_source, item.checker, item.remark)
    AuditLogService.record_operation(db, "stocktake", "exception_report", item.checker or "system", "stocktake_item", item.asset_id, f"{task.id} 异常上报 {item.asset_id}", item.remark)
    refresh_task_status(task)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/items/{asset_id}/review")
def review_exception(task_id: str, asset_id: str, payload: StocktakeReviewSubmit, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    item = next((row for row in task.items if row.asset_id == asset_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    if item.result == "正常":
        item.review_status = "无需复核"
    else:
        item.review_status = payload.review_status if payload.review_status in {"已确认", "已驳回", "待复核"} else "已确认"
    item.review_note = payload.review_note or ""
    item.reviewed_by = payload.reviewer or task.owner or "资产管理员"
    item.reviewed_at = datetime.utcnow()
    AuditLogService.record_operation(db, "stocktake", "exception_review", item.reviewed_by, "stocktake_item", item.asset_id, f"{task.id} 复核 {item.asset_id}: {item.review_status}", item.review_note)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/finish")
def finish_task(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    for item in task.items:
        if item.result == "未盘":
            item.result = "盘亏"
            item.actual_location = ""
            item.checker = task.owner or "资产管理员"
            item.checked_at = datetime.utcnow()
            item.remark = item.remark or "完成盘点时未扫描确认，自动标记为盘亏"
            item.review_status = "待复核"
    task.status = "已完成"
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.get("/tasks/{task_id}/scan-logs")
def list_scan_logs(task_id: str, db: Session = Depends(get_db)):
    rows = db.query(StocktakeScanLog).filter(StocktakeScanLog.task_id == task_id).order_by(StocktakeScanLog.created_at.desc()).limit(500).all()
    return [
        {
            "id": row.id,
            "task_id": row.task_id,
            "asset_id": row.asset_id or "",
            "scan_raw": row.scan_raw or "",
            "parsed_code": row.parsed_code or "",
            "result": row.result or "",
            "client_source": row.client_source or "",
            "operator": row.operator or "",
            "message": row.message or "",
            "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else "",
        }
        for row in rows
    ]


def scoped_assets(db: Session, scope: str, target: str | list[str] | None, user_context: dict | None = None, include_scrapped: bool = False, include_disposed: bool = False):
    query = AssetService.apply_data_scope(db.query(Asset), user_context)
    targets = normalize_targets(target)
    excluded_statuses = []
    if not include_scrapped:
        excluded_statuses.append("scrapped")
    if not include_disposed:
        excluded_statuses.append("disposed")
    if excluded_statuses:
        query = query.filter(~Asset.status.in_(excluded_statuses))
    if scope == "部门" and targets:
        query = query.filter(Asset.dept_id.in_(targets))
    if scope == "仓库" and targets:
        query = query.filter(Asset.location.in_(targets))
    if scope == "状态" and targets:
        query = query.filter(Asset.status.in_(targets))
    return query.order_by(Asset.asset_id.asc()).all()


def normalize_targets(target: str | list[str] | None = None, targets: list[str] | None = None) -> list[str]:
    values: list[str] = []
    if isinstance(target, list):
        values.extend(target)
    elif target:
        values.extend(str(target).replace(",", "、").split("、"))
    if targets:
        values.extend(targets)
    clean = [str(value).strip() for value in values if str(value or "").strip()]
    return list(dict.fromkeys(clean))


def get_task(db: Session, task_id: str) -> StocktakeTask:
    task = db.query(StocktakeTask).options(joinedload(StocktakeTask.items)).filter(StocktakeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    return task


def refresh_task_status(task: StocktakeTask) -> None:
    total = len(task.items)
    checked = len([item for item in task.items if item.result != "未盘"])
    if task.status != "已完成" and total and checked == total:
        task.status = "待确认"


def record_scan_log(db: Session, task_id: str, asset_id: str | None, scan_raw: str | None, parsed_code: str | None, result: str, client_source: str | None, operator: str | None, message: str | None) -> None:
    db.add(
        StocktakeScanLog(
            task_id=task_id,
            asset_id=asset_id,
            scan_raw=scan_raw or "",
            parsed_code=parsed_code or "",
            result=result,
            client_source=client_source or "",
            operator=operator or "",
            message=message or "",
        )
    )


def serialize_task(task: StocktakeTask, visible_asset_ids: set[str] | None = None) -> dict:
    items = [item for item in task.items if visible_asset_ids is None or item.asset_id in visible_asset_ids]
    checked = len([item for item in items if item.result != "未盘"])
    abnormal = len([item for item in items if item.result in {"盘盈", "盘亏", "位置不符", "状态不符"}])
    return {
        "id": task.id,
        "name": task.name,
        "scope": task.scope,
        "target": task.target or "",
        "owner": task.owner or "",
        "status": task.status,
        "created_at": task.created_at.date().isoformat() if task.created_at else "",
        "total": len(items),
        "checked": checked,
        "abnormal": abnormal,
        "items": [serialize_item(item) for item in items],
    }


def visible_asset_id_set(db: Session, request: Request) -> set[str]:
    return {row[0] for row in AssetService.apply_data_scope(db.query(Asset), user_context_from_request(request)).with_entities(Asset.asset_id).all()}


def serialize_item(item: StocktakeItem) -> dict:
    return {
        "asset_id": item.asset_id,
        "name": item.name or "",
        "sn": item.sn or "",
        "book_location": item.book_location or "",
        "book_status": item.book_status or "",
        "actual_location": item.actual_location or "",
        "result": item.result,
        "checker": item.checker or "",
        "checked_at": item.checked_at.isoformat(sep=" ", timespec="seconds") if item.checked_at else "",
        "remark": item.remark or "",
        "review_status": item.review_status or "无需复核",
        "review_note": item.review_note or "",
        "reviewed_by": item.reviewed_by or "",
        "reviewed_at": item.reviewed_at.isoformat(sep=" ", timespec="seconds") if item.reviewed_at else "",
    }
