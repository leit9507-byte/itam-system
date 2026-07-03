import csv
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.asset import Asset
from app.models.repair import RepairRecord
from app.models.stocktake import StocktakeItem, StocktakeTask


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/assets.csv")
def export_assets_csv(db: Session = Depends(get_db)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["asset_id", "asset_no", "name", "category", "brand", "model", "sn", "status", "owner_user_id", "dept_id", "location", "purchase_price"])
    for asset in db.query(Asset).order_by(Asset.asset_id.asc()).all():
        writer.writerow([asset.asset_id, asset.asset_no, asset.name, asset.category, asset.brand, asset.model, asset.sn, asset.status, asset.owner_user_id, asset.dept_id, asset.location, asset.purchase_price])
    return PlainTextResponse(output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=assets.csv"})


@router.get("/assets.pdf")
def export_assets_pdf(db: Session = Depends(get_db)):
    output_dir = Path(get_settings().upload_dir) / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "assets.pdf"
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "ITAM Asset Report")
    y -= 28
    c.setFont("Helvetica", 9)
    for asset in db.query(Asset).order_by(Asset.asset_id.asc()).all():
        line = f"{asset.asset_id} | {asset.name} | {asset.category} | {asset.status} | {asset.owner_user_id or '-'} | {asset.location or '-'}"
        c.drawString(40, y, line[:120])
        y -= 16
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 40
    c.save()
    return FileResponse(output_path, filename="assets.pdf", media_type="application/pdf")


@router.get("/analytics")
def report_analytics(db: Session = Depends(get_db)):
    department_rows = (
        db.query(
            Asset.dept_id,
            func.count(Asset.asset_id),
            func.coalesce(func.sum(Asset.purchase_price), 0),
            func.count(func.distinct(Asset.owner_user_id)),
        )
        .filter(Asset.status != "scrapped")
        .group_by(Asset.dept_id)
        .order_by(func.count(Asset.asset_id).desc())
        .all()
    )
    department_occupancy = [
        {
            "dept_id": dept_id or "未绑定",
            "asset_count": int(asset_count or 0),
            "asset_value": float(asset_value or 0),
            "owner_count": int(owner_count or 0),
            "per_capita_value": float(asset_value or 0) / max(int(owner_count or 0), 1),
        }
        for dept_id, asset_count, asset_value, owner_count in department_rows
    ]
    months = month_windows(6)
    idle_trend = [
        {
            "month": month,
            "count": db.query(func.count(Asset.asset_id))
            .filter(Asset.status.in_(["idle", "in_stock"]), Asset.created_at <= end_at)
            .scalar()
            or 0,
        }
        for month, _start_at, end_at in months
    ]
    repair_cost_trend = [
        {
            "month": month,
            "cost": float(
                db.query(func.coalesce(func.sum(RepairRecord.repair_cost), 0))
                .filter(RepairRecord.repair_time >= start_at, RepairRecord.repair_time < end_at)
                .scalar()
                or 0
            ),
        }
        for month, start_at, end_at in months
    ]
    stocktake_diff_trend = [
        {
            "month": month,
            "diff_count": int(
                db.query(func.count(StocktakeItem.id))
                .join(StocktakeTask, StocktakeItem.task_id == StocktakeTask.id)
                .filter(StocktakeTask.created_at >= start_at, StocktakeTask.created_at < end_at, StocktakeItem.result != "正常")
                .scalar()
                or 0
            ),
        }
        for month, start_at, end_at in months
    ]
    return {
        "department_occupancy": department_occupancy,
        "per_capita_value": department_occupancy,
        "idle_trend": idle_trend,
        "repair_cost_trend": repair_cost_trend,
        "stocktake_diff_trend": stocktake_diff_trend,
    }


def month_windows(count: int) -> list[tuple[str, datetime, datetime]]:
    today = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts = []
    current = today
    for _ in range(count - 1):
        starts.append(current)
        current = (current - timedelta(days=1)).replace(day=1)
    starts.append(current)
    starts = list(reversed(starts))
    windows = []
    for start in starts:
        end = datetime(start.year + 1, 1, 1) if start.month == 12 else datetime(start.year, start.month + 1, 1)
        windows.append((start.strftime("%Y-%m"), start, end))
    return windows
