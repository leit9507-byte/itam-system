from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset
from app.models.lifecycle import Lifecycle


router = APIRouter(prefix="/lifecycle", tags=["Lifecycle"])


@router.get("/list")
def list_lifecycles(
    asset_id: str | None = None,
    company: str | None = None,
    keyword: str | None = None,
    operation_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Lifecycle, Asset).join(Asset, Asset.asset_id == Lifecycle.asset_id)
    if asset_id:
        query = query.filter(Lifecycle.asset_id == asset_id)
    if company:
        query = query.filter(Asset.company == company)
    if operation_type == "daily_inventory":
        query = query.filter(Lifecycle.action_type == "STATUS_CHANGE")
    if operation_type == "other":
        query = query.filter(Lifecycle.action_type != "STATUS_CHANGE")
    clean_keyword = (keyword or "").strip()
    if clean_keyword:
        pattern = f"%{clean_keyword}%"
        query = query.filter(
            or_(
                Lifecycle.asset_id.like(pattern),
                Lifecycle.action_type.like(pattern),
                Lifecycle.operator.like(pattern),
                Lifecycle.remark.like(pattern),
                Asset.name.like(pattern),
                Asset.company.like(pattern),
            )
        )
    if start_date:
        query = query.filter(Lifecycle.timestamp >= datetime.combine(datetime.fromisoformat(start_date).date(), time.min))
    if end_date:
        query = query.filter(Lifecycle.timestamp <= datetime.combine(datetime.fromisoformat(end_date).date(), time.max))
    total = query.count()
    query = query.order_by(Lifecycle.timestamp.desc())
    if page_size and page_size > 0:
        query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
    rows = query.all()
    items = [
        {
            "id": lifecycle.id,
            "asset_id": lifecycle.asset_id,
            "asset_name": asset.name,
            "company": asset.company,
            "type": lifecycle.action_type,
            "from_status": lifecycle.from_status,
            "to_status": lifecycle.to_status,
            "status": lifecycle.to_status or lifecycle.from_status,
            "operator": lifecycle.operator,
            "time": lifecycle.timestamp,
            "description": lifecycle.remark or f"{lifecycle.from_status or '-'} -> {lifecycle.to_status or '-'}",
        }
        for lifecycle, asset in rows
    ]
    return {"list": items, "total": total, "page": max(page, 1), "page_size": page_size or total}
