from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.asset import Asset
from app.models.stocktake import StocktakeItem, StocktakeTask


router = APIRouter(prefix="/stocktake", tags=["Stocktake"])


class StocktakeTaskCreate(BaseModel):
    name: str
    scope: str = "全部"
    target: str | None = None
    owner: str | None = None


class StocktakeItemSubmit(BaseModel):
    actual_location: str | None = None
    result: str = "正常"
    checker: str | None = None
    remark: str | None = None


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = (
        db.query(StocktakeTask)
        .options(joinedload(StocktakeTask.items))
        .order_by(StocktakeTask.created_at.desc())
        .all()
    )
    return [serialize_task(task) for task in tasks]


@router.post("/tasks")
def create_task(payload: StocktakeTaskCreate, db: Session = Depends(get_db)):
    task_id = f"ST-{datetime.utcnow().year}-{db.query(StocktakeTask).count() + 1:03d}"
    task = StocktakeTask(
        id=task_id,
        name=payload.name,
        scope=payload.scope,
        target=payload.target or "",
        owner=payload.owner or "资产管理员",
        status="待开始",
    )
    for asset in scoped_assets(db, payload.scope, payload.target):
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
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.post("/tasks/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task.status == "待开始":
        task.status = "进行中"
        db.commit()
        db.refresh(task)
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
    refresh_task_status(task)
    db.commit()
    db.refresh(task)
    return serialize_item(item)


@router.post("/tasks/{task_id}/finish")
def finish_task(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    task.status = "已完成"
    db.commit()
    db.refresh(task)
    return serialize_task(task)


def scoped_assets(db: Session, scope: str, target: str | None):
    query = db.query(Asset)
    if scope == "部门" and target:
        query = query.filter(Asset.dept_id == target)
    if scope == "仓库" and target:
        query = query.filter(Asset.location == target)
    if scope == "状态" and target:
        query = query.filter(Asset.status == target)
    return query.order_by(Asset.asset_id.asc()).all()


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


def serialize_task(task: StocktakeTask) -> dict:
    checked = len([item for item in task.items if item.result != "未盘"])
    abnormal = len([item for item in task.items if item.result in {"盘盈", "盘亏", "位置不符", "状态不符"}])
    return {
        "id": task.id,
        "name": task.name,
        "scope": task.scope,
        "target": task.target or "",
        "owner": task.owner or "",
        "status": task.status,
        "created_at": task.created_at.date().isoformat() if task.created_at else "",
        "total": len(task.items),
        "checked": checked,
        "abnormal": abnormal,
        "items": [serialize_item(item) for item in task.items],
    }


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
    }
