from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset


router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/list")
def list_companies(db: Session = Depends(get_db)):
    assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
    groups = defaultdict(list)
    for asset in assets:
        groups[asset.company or "未设置公司"].append(asset)

    rows = []
    for name, items in groups.items():
        status_counter = Counter(asset.status or "unknown" for asset in items)
        rows.append(
            {
                "name": name,
                "asset_count": len(items),
                "total_original_value": sum(asset.purchase_price or 0 for asset in items),
                "in_use_count": status_counter.get("in_use", 0),
                "in_stock_count": status_counter.get("in_stock", 0),
                "idle_count": status_counter.get("idle", 0),
                "repair_count": status_counter.get("repair", 0),
                "scrapped_count": status_counter.get("scrapped", 0),
                "pending_scrap_count": status_counter.get("pending_scrap", 0),
                "status_distribution": [{"name": key, "value": value} for key, value in status_counter.items()],
                "assets": [
                    {
                        "asset_id": asset.asset_id,
                        "name": asset.name,
                        "category": asset.category,
                        "brand": asset.brand,
                        "model": asset.model,
                        "sn": asset.sn,
                        "status": asset.status,
                        "owner_user_id": asset.owner_user_id,
                        "dept_id": asset.dept_id,
                        "location": asset.location,
                        "purchase_price": asset.purchase_price or 0,
                        "purchase_supplier_name": asset.purchase_supplier_name,
                        "created_at": asset.created_at,
                    }
                    for asset in items
                ],
            }
        )
    return sorted(rows, key=lambda item: item["asset_count"], reverse=True)
