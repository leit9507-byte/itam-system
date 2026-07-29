from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.asset import Asset
from app.models.stocktake import StocktakeItem, StocktakeScanLog, StocktakeTask
from app.models.user import UserDirectory
from app.schemas.asset import AssetUpdate
from app.services.audit_log_service import AuditLogService
from app.services.asset_service import AssetService, AssetValidationError
from app.services.notification_service import NotificationService
from app.services.number_service import NumberService


router = APIRouter(prefix="/stocktake", tags=["Stocktake"])


class StocktakeTaskCreate(BaseModel):
    name: str
    scope: str = "全部"
    target: str | None = None
    targets: list[str] = Field(default_factory=list)
    owner: str | None = None
    include_scrapped: bool = False


class StocktakeItemSubmit(BaseModel):
    actual_location: str | None = None
    actual_owner_user_id: str | None = None
    update_asset_info: bool = False
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
    year = datetime.utcnow().year
    task_id = NumberService.next(db, f"stocktake:{year}", f"ST-{year}-", 3)
    targets = normalize_targets(payload.target, payload.targets)
    task = StocktakeTask(
        id=task_id,
        name=payload.name,
        scope=payload.scope,
        target="、".join(targets),
        owner=payload.owner or "资产管理员",
        status="待开始",
    )
    for asset in scoped_assets(db, payload.scope, targets, user_context_from_request(request), payload.include_scrapped):
        task.items.append(
            StocktakeItem(
                asset_id=asset.asset_id,
                name=asset.name,
                sn=asset.sn,
                book_location=asset.location or "",
                book_status=asset.status,
                book_owner_user_id=asset.owner_user_id or "",
                result="未盘",
            )
        )
    db.add(task)
    AuditLogService.record_operation(db, "stocktake", "create_task", operator_from_request(request), "stocktake_task", task.id, f"创建盘点任务 {task.id}", payload.model_dump())
    db.commit()
    db.refresh(task)
    return serialize_task(task, visible_asset_id_set(db, request))


@router.post("/tasks/{task_id}/start")
def start_task(task_id: str, request: Request, db: Session = Depends(get_db)):
    task, visible_asset_ids = get_scoped_task(db, task_id, request, require_full_scope=True)
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
    return serialize_task(task, visible_asset_ids)


@router.post("/tasks/{task_id}/items/{asset_id}")
def submit_item(task_id: str, asset_id: str, payload: StocktakeItemSubmit, request: Request, db: Session = Depends(get_db)):
    task, visible_asset_ids = get_scoped_task(db, task_id, request)
    item = next((row for row in task.items if row.asset_id == asset_id or row.sn == asset_id), None)
    if not item or item.asset_id not in visible_asset_ids:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    ensure_task_accepts_items(task, visible_asset_ids)
    asset = AssetService.get_scoped_asset(db, item.asset_id, user_context_from_request(request))
    operator = operator_from_request(request)
    if item.book_owner_user_id is None:
        item.book_owner_user_id = asset.owner_user_id or ""
    actual_location = (payload.actual_location or "").strip()
    actual_owner_user_id = (
        AssetService.normalize_blank(payload.actual_owner_user_id)
        if payload.actual_owner_user_id is not None
        else AssetService.normalize_blank(item.book_owner_user_id)
    )
    if actual_owner_user_id:
        user = db.query(UserDirectory).filter(UserDirectory.user_id == actual_owner_user_id, UserDirectory.status == "active").first()
        if not user:
            raise HTTPException(status_code=400, detail="选择的使用人不存在或已离职")

    location_mismatch = actual_location != (item.book_location or "").strip()
    owner_mismatch = actual_owner_user_id != AssetService.normalize_blank(item.book_owner_user_id)
    item.actual_location = actual_location
    item.actual_owner_user_id = actual_owner_user_id
    item.result = normalize_stocktake_result(payload.result, owner_mismatch, location_mismatch)
    item.checker = operator
    item.checked_at = datetime.utcnow()
    item.remark = payload.remark or ""
    item.asset_info_updated = False

    updated_fields: list[str] = []
    owner_needs_update = actual_owner_user_id != AssetService.normalize_blank(asset.owner_user_id)
    location_needs_update = actual_location != (asset.location or "").strip()
    if payload.update_asset_info:
        updates: dict = {}
        if owner_needs_update:
            updates["owner_user_id"] = actual_owner_user_id
            updated_fields.append("使用人")
        if location_needs_update:
            updates["location"] = actual_location
            updated_fields.append("位置")
        if updates:
            try:
                AssetService.apply_asset_update(
                    db,
                    asset.asset_id,
                    AssetUpdate(**updates),
                    operator,
                    user_context_from_request(request),
                    source=f"stocktake:{task.id}",
                )
            except AssetValidationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            item.asset_info_updated = True
            correction_note = f"盘点时已同步更新资产{'、'.join(updated_fields)}"
            item.remark = "；".join(part for part in [item.remark, correction_note] if part)
        elif owner_mismatch or location_mismatch:
            item.remark = "；".join(part for part in [item.remark, "已核对当前资产台账，无需重复更新"] if part)

    if item.result == "正常":
        item.review_status = "无需复核"
    elif payload.update_asset_info:
        item.review_status = "已确认"
        item.review_note = item.remark
        item.reviewed_by = operator
        item.reviewed_at = datetime.utcnow()
    else:
        item.review_status = "待复核"
    record_scan_log(db, task.id, item.asset_id, payload.scan_raw, payload.parsed_code or asset_id, item.result, payload.client_source, item.checker, "扫码登记")
    AuditLogService.record_operation(
        db,
        "stocktake",
        "scan_submit",
        item.checker or "system",
        "stocktake_item",
        item.asset_id,
        f"{task.id} 扫码登记 {item.asset_id}",
        {
            "result": item.result,
            "book_owner_user_id": item.book_owner_user_id or "",
            "actual_owner_user_id": item.actual_owner_user_id or "",
            "book_location": item.book_location or "",
            "actual_location": item.actual_location or "",
            "asset_info_updated": item.asset_info_updated,
            "updated_fields": updated_fields,
        },
    )
    refresh_task_status(task)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/items/{asset_id}/exception")
def report_exception(task_id: str, asset_id: str, payload: StocktakeExceptionSubmit, request: Request, db: Session = Depends(get_db)):
    task, visible_asset_ids = get_scoped_task(db, task_id, request)
    item = next((row for row in task.items if row.asset_id == asset_id or row.sn == asset_id), None)
    if not item or item.asset_id not in visible_asset_ids:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    ensure_task_accepts_items(task, visible_asset_ids)
    item.actual_location = payload.actual_location or ""
    item.result = payload.result if payload.result in {"盘盈", "盘亏", "位置不符", "使用人不符", "状态不符"} else "位置不符"
    item.checker = operator_from_request(request)
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
def review_exception(task_id: str, asset_id: str, payload: StocktakeReviewSubmit, request: Request, db: Session = Depends(get_db)):
    task, visible_asset_ids = get_scoped_task(db, task_id, request)
    item = next((row for row in task.items if row.asset_id == asset_id), None)
    if not item or item.asset_id not in visible_asset_ids:
        raise HTTPException(status_code=404, detail="该资产不在当前盘点任务范围内")
    if item.result == "正常":
        item.review_status = "无需复核"
    else:
        item.review_status = payload.review_status if payload.review_status in {"已确认", "已驳回", "待复核"} else "已确认"
    item.review_note = payload.review_note or ""
    item.reviewed_by = operator_from_request(request)
    item.reviewed_at = datetime.utcnow()
    AuditLogService.record_operation(db, "stocktake", "exception_review", item.reviewed_by, "stocktake_item", item.asset_id, f"{task.id} 复核 {item.asset_id}: {item.review_status}", item.review_note)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/finish")
def finish_task(task_id: str, request: Request, db: Session = Depends(get_db)):
    task, visible_asset_ids = get_scoped_task(db, task_id, request, require_full_scope=True)
    for item in task.items:
        if item.result == "未盘":
            item.result = "盘亏"
            item.actual_location = ""
            item.checker = operator_from_request(request)
            item.checked_at = datetime.utcnow()
            item.remark = item.remark or "完成盘点时未扫描确认，自动标记为盘亏"
            item.review_status = "待复核"
    task.status = "已完成"
    db.commit()
    db.refresh(task)
    return serialize_task(task, visible_asset_ids)


@router.get("/tasks/{task_id}/scan-logs")
def list_scan_logs(task_id: str, request: Request, db: Session = Depends(get_db)):
    _, visible_asset_ids = get_scoped_task(db, task_id, request)
    rows = (
        db.query(StocktakeScanLog)
        .filter(StocktakeScanLog.task_id == task_id, StocktakeScanLog.asset_id.in_(visible_asset_ids))
        .order_by(StocktakeScanLog.created_at.desc())
        .limit(500)
        .all()
    )
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


@router.get("/tasks/{task_id}/items")
def list_task_items(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    keyword: str | None = None,
    result: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    task, visible_asset_ids = get_scoped_task(db, task_id, request)
    query = db.query(StocktakeItem).filter(
        StocktakeItem.task_id == task.id,
        StocktakeItem.asset_id.in_(visible_asset_ids),
    )
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                StocktakeItem.asset_id.ilike(pattern),
                StocktakeItem.name.ilike(pattern),
                StocktakeItem.sn.ilike(pattern),
                StocktakeItem.book_location.ilike(pattern),
                StocktakeItem.actual_location.ilike(pattern),
                StocktakeItem.remark.ilike(pattern),
            )
        )
    if result:
        query = query.filter(StocktakeItem.result == result)
    total = query.count()
    rows = (
        query.order_by(StocktakeItem.asset_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    asset_ids = [item.asset_id for item in rows if item.asset_id]
    asset_numbers = {
        asset.asset_id: asset.asset_no
        for asset in db.query(Asset).filter(Asset.asset_id.in_(asset_ids)).all()
    } if asset_ids else {}
    return {"list": [serialize_item(item, asset_numbers.get(item.asset_id)) for item in rows], "total": total, "page": page, "page_size": page_size}


def scoped_assets(db: Session, scope: str, target: str | list[str] | None, user_context: dict | None = None, include_scrapped: bool = False):
    query = AssetService.apply_data_scope(db.query(Asset), user_context)
    targets = normalize_targets(target)
    excluded_statuses = []
    if not include_scrapped:
        excluded_statuses.append("scrapped")
    excluded_statuses.append("disposed")
    excluded_statuses.append("lost")
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


def get_scoped_task(db: Session, task_id: str, request: Request, require_full_scope: bool = False) -> tuple[StocktakeTask, set[str]]:
    task = get_task(db, task_id)
    visible_asset_ids = visible_asset_id_set(db, request)
    task_asset_ids = {item.asset_id for item in task.items}
    visible_task_asset_ids = task_asset_ids & visible_asset_ids
    if not visible_task_asset_ids:
        raise HTTPException(status_code=404, detail="盘点任务不存在")
    if require_full_scope and visible_task_asset_ids != task_asset_ids:
        raise HTTPException(status_code=403, detail="不能启动或完成包含数据范围外资产的盘点任务")
    return task, visible_asset_ids


def refresh_task_status(task: StocktakeTask) -> None:
    total = len(task.items)
    checked = len([item for item in task.items if item.result != "未盘"])
    if task.status != "已完成" and total and checked == total:
        task.status = "待确认"


def ensure_task_accepts_items(task: StocktakeTask, visible_asset_ids: set[str]) -> None:
    if task.status == "已完成":
        raise HTTPException(status_code=400, detail="已完成的盘点任务不能继续登记")
    if task.status != "待开始":
        return
    task_asset_ids = {item.asset_id for item in task.items}
    if not task_asset_ids.issubset(visible_asset_ids):
        raise HTTPException(status_code=403, detail="跨部门盘点任务需由具有全局数据权限的管理员先启动")
    task.status = "进行中"


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
    is_partial = visible_asset_ids is not None and len(items) != len(task.items)
    checked = len([item for item in items if item.result != "未盘"])
    abnormal = len([item for item in items if item.result in {"盘盈", "盘亏", "位置不符", "使用人不符", "状态不符"}])
    return {
        "id": task.id,
        "name": task.name,
        "scope": task.scope,
        "target": "当前数据范围" if is_partial else task.target or "",
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


def serialize_item(item: StocktakeItem, asset_no: str | None = None) -> dict:
    return {
        "asset_id": item.asset_id,
        "asset_no": asset_no or item.asset_id,
        "name": item.name or "",
        "sn": item.sn or "",
        "book_location": item.book_location or "",
        "book_status": item.book_status or "",
        "book_owner_user_id": item.book_owner_user_id or "",
        "actual_location": item.actual_location or "",
        "actual_owner_user_id": item.actual_owner_user_id or "",
        "asset_info_updated": bool(item.asset_info_updated),
        "result": item.result,
        "checker": item.checker or "",
        "checked_at": item.checked_at.isoformat(sep=" ", timespec="seconds") if item.checked_at else "",
        "remark": item.remark or "",
        "review_status": item.review_status or "无需复核",
        "review_note": item.review_note or "",
        "reviewed_by": item.reviewed_by or "",
        "reviewed_at": item.reviewed_at.isoformat(sep=" ", timespec="seconds") if item.reviewed_at else "",
    }


def normalize_stocktake_result(requested_result: str, owner_mismatch: bool, location_mismatch: bool) -> str:
    if requested_result not in {"", "正常"}:
        return requested_result
    if owner_mismatch:
        return "使用人不符"
    if location_mismatch:
        return "位置不符"
    return "正常"
