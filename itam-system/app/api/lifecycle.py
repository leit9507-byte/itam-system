from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset
from app.models.lifecycle import Lifecycle


router = APIRouter(prefix="/lifecycle", tags=["Lifecycle"])


@router.get("/list")
def list_lifecycles(asset_id: str | None = None, company: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Lifecycle, Asset).join(Asset, Asset.asset_id == Lifecycle.asset_id)
    if asset_id:
        query = query.filter(Lifecycle.asset_id == asset_id)
    if company:
        query = query.filter(Asset.company == company)
    rows = query.order_by(Lifecycle.timestamp.desc()).limit(500).all()
    return [
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
