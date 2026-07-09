from datetime import datetime
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import secure_filename
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.asset import Asset
from app.models.file import AssetAttachment
from app.services.asset_service import AssetService
from app.services.audit_log_service import AuditLogService


router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/asset/{asset_id}/upload")
async def upload_asset_file(asset_id: str, request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not can_access_asset(db, asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="asset not found")
    settings = get_settings()
    upload_root = Path(get_settings().upload_dir) / asset_id
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename or "attachment")
    validate_upload_file(filename)
    storage_path = upload_root / filename
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"file too large, max {settings.max_upload_size_mb} MB")
    storage_path.write_bytes(content)
    operator = operator_from_request(request)
    row = AssetAttachment(
        asset_id=asset_id,
        filename=filename,
        content_type=file.content_type,
        storage_path=str(storage_path),
        size=len(content),
        uploaded_by=operator,
    )
    db.add(row)
    AuditLogService.record_operation(db, "file", "upload", operator, "asset_attachment", asset_id, f"上传附件 {filename}")
    db.commit()
    db.refresh(row)
    return row


@router.get("/asset/{asset_id}")
def list_asset_files(
    asset_id: str,
    request: Request,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    db: Session = Depends(get_db),
):
    if not can_access_asset(db, asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="asset not found")
    query = db.query(AssetAttachment).filter(AssetAttachment.asset_id == asset_id)
    if status:
        query = query.filter(AssetAttachment.status == status)
    else:
        query = query.filter(AssetAttachment.status != "deleted")
    query = query.order_by(AssetAttachment.created_at.desc(), AssetAttachment.id.desc())
    if page_size is None:
        return query.all()
    clean_page = max(page or 1, 1)
    clean_page_size = min(max(page_size, 1), 200)
    total = query.count()
    rows = query.offset((clean_page - 1) * clean_page_size).limit(clean_page_size).all()
    return {"list": rows, "total": total, "page": clean_page, "page_size": clean_page_size}


@router.get("/{file_id}/download")
def download_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(AssetAttachment, file_id)
    if not row or row.status == "deleted" or not Path(row.storage_path).exists():
        raise HTTPException(status_code=404, detail="file not found")
    if not can_access_asset(db, row.asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(row.storage_path, filename=row.filename, media_type=row.content_type)


@router.post("/{file_id}/archive")
def archive_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(AssetAttachment, file_id)
    if not row or row.status == "deleted":
        raise HTTPException(status_code=404, detail="file not found")
    if not can_access_asset(db, row.asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="file not found")
    row.status = "archived"
    row.archived_at = datetime.utcnow()
    AuditLogService.record_operation(db, "file", "archive", operator_from_request(request), "asset_attachment", str(row.id), f"归档附件 {row.filename}")
    db.commit()
    db.refresh(row)
    return row


@router.post("/{file_id}/restore")
def restore_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(AssetAttachment, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="file not found")
    if not can_access_asset(db, row.asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="file not found")
    row.status = "active"
    row.deleted_at = None
    AuditLogService.record_operation(db, "file", "restore", operator_from_request(request), "asset_attachment", str(row.id), f"恢复附件 {row.filename}")
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{file_id}")
def delete_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(AssetAttachment, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="file not found")
    if not can_access_asset(db, row.asset_id, user_context_from_request(request)):
        raise HTTPException(status_code=404, detail="file not found")
    row.status = "deleted"
    row.deleted_at = datetime.utcnow()
    AuditLogService.record_operation(db, "file", "delete", operator_from_request(request), "asset_attachment", str(row.id), f"删除附件 {row.filename}")
    db.commit()
    return {"ok": True}


@router.get("/asset/{asset_id}/qrcode")
def asset_qrcode(asset_id: str, request: Request, db: Session = Depends(get_db)):
    asset = can_access_asset(db, asset_id, user_context_from_request(request))
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    output_dir = Path(get_settings().upload_dir) / "qrcodes"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{secure_filename(asset_id)}.png"
    img = qrcode.make(f"ITAM-ASSET:{asset.asset_id}|{asset.name}|{asset.sn or ''}")
    img.save(output_path)
    return FileResponse(output_path, filename=f"{asset_id}.png", media_type="image/png")


def can_access_asset(db: Session, asset_id: str, user_context: dict | None) -> Asset | None:
    return AssetService.apply_data_scope(db.query(Asset), user_context).filter(Asset.asset_id == asset_id).first()


def validate_upload_file(filename: str) -> None:
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    blocked = {".exe", ".bat", ".cmd", ".com", ".ps1", ".sh", ".js", ".mjs", ".vbs", ".msi", ".dll", ".scr", ".jar", ".py"}
    if suffix in blocked:
        raise HTTPException(status_code=400, detail="不允许上传可执行或脚本文件")
    if settings.allowed_upload_extensions and suffix not in settings.allowed_upload_extensions:
        raise HTTPException(status_code=400, detail=f"不允许的文件类型：{suffix or '无扩展名'}")
