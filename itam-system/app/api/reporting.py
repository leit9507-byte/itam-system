import csv
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.asset import Asset


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/assets.csv")
def export_assets_csv(db: Session = Depends(get_db)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["asset_id", "name", "category", "brand", "model", "sn", "status", "owner_user_id", "dept_id", "location", "purchase_price"])
    for asset in db.query(Asset).order_by(Asset.asset_id.asc()).all():
        writer.writerow([asset.asset_id, asset.name, asset.category, asset.brand, asset.model, asset.sn, asset.status, asset.owner_user_id, asset.dept_id, asset.location, asset.purchase_price])
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
