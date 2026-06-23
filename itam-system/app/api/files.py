from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import secure_filename
from app.core.config import get_settings
from app.core.database import get_db
from app.models.asset import Asset
from app.models.file import AssetAttachment


router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/asset/{asset_id}/upload")
async def upload_asset_file(asset_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Asset, asset_id):
        raise HTTPException(status_code=404, detail="asset not found")
    upload_root = Path(get_settings().upload_dir) / asset_id
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename or "attachment")
    storage_path = upload_root / filename
    content = await file.read()
    storage_path.write_bytes(content)
    row = AssetAttachment(
        asset_id=asset_id,
        filename=filename,
        content_type=file.content_type,
        storage_path=str(storage_path),
        size=len(content),
        uploaded_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/asset/{asset_id}")
def list_asset_files(asset_id: str, db: Session = Depends(get_db)):
    return db.query(AssetAttachment).filter(AssetAttachment.asset_id == asset_id).order_by(AssetAttachment.created_at.desc()).all()


@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    row = db.get(AssetAttachment, file_id)
    if not row or not Path(row.storage_path).exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(row.storage_path, filename=row.filename, media_type=row.content_type)


@router.get("/asset/{asset_id}/qrcode")
def asset_qrcode(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    output_dir = Path(get_settings().upload_dir) / "qrcodes"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{secure_filename(asset_id)}.png"
    img = qrcode.make(f"ITAM-ASSET:{asset.asset_id}|{asset.name}|{asset.sn or ''}")
    img.save(output_path)
    return FileResponse(output_path, filename=f"{asset_id}.png", media_type="image/png")
