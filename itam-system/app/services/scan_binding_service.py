import hashlib
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.scan_binding import AssetScanBinding
from app.services.asset_service import AssetService
from app.services.audit_log_service import AuditLogService


class ScanBindingService:
    QUERY_KEYS = ("asset_id", "assetId", "code", "sn", "id")
    PATH_MARKERS = {"hardware", "asset", "assets"}

    @staticmethod
    def extract_scan_value(value: str) -> str:
        text = (value or "").strip()
        if not text:
            return ""

        tagged = re.search(r"ITAM-ASSET:([^|]+)", text, re.IGNORECASE)
        if tagged and tagged.group(1):
            return tagged.group(1).strip()

        parsed = urlparse(text)
        if parsed.scheme and parsed.netloc:
            params = parse_qs(parsed.query)
            for key in ScanBindingService.QUERY_KEYS:
                values = params.get(key)
                if values and values[0]:
                    return values[0].strip()
            segments = [item for item in parsed.path.split("/") if item]
            lower_segments = [item.lower() for item in segments]
            for index, segment in enumerate(lower_segments):
                if segment in ScanBindingService.PATH_MARKERS and index + 1 < len(segments):
                    return segments[index + 1].strip()
            if segments:
                return segments[-1].strip()

        return text

    @staticmethod
    def normalize_scan_key(value: str) -> str:
        extracted = ScanBindingService.extract_scan_value(value)
        clean = " ".join(extracted.strip().lower().split())
        if not clean:
            raise ValueError("scan content is empty")
        if len(clean) <= 240:
            return clean
        return "sha256:" + hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @staticmethod
    def to_out(row: AssetScanBinding) -> dict:
        return {
            "id": row.id,
            "asset_id": row.asset_id,
            "scan_key": row.scan_key,
            "scan_raw": row.scan_raw,
            "scan_type": row.scan_type,
            "status": row.status,
            "remark": row.remark,
            "created_by": row.created_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def can_access_asset(db: Session, asset_id: str, user_context: dict | None) -> Asset | None:
        return AssetService.apply_data_scope(db.query(Asset), user_context).filter(Asset.asset_id == asset_id).first()

    @staticmethod
    def list_for_asset(db: Session, asset_id: str, user_context: dict | None) -> list[dict]:
        if not ScanBindingService.can_access_asset(db, asset_id, user_context):
            raise HTTPException(status_code=404, detail="asset not found")
        rows = (
            db.query(AssetScanBinding)
            .filter(AssetScanBinding.asset_id == asset_id, AssetScanBinding.status == "active")
            .order_by(AssetScanBinding.updated_at.desc(), AssetScanBinding.id.desc())
            .all()
        )
        return [ScanBindingService.to_out(row) for row in rows]

    @staticmethod
    def bind_to_asset(
        db: Session,
        asset_id: str,
        scan_raw: str,
        scan_type: str,
        remark: str | None,
        force: bool,
        operator: str,
        user_context: dict | None,
    ) -> dict:
        if not ScanBindingService.can_access_asset(db, asset_id, user_context):
            raise HTTPException(status_code=404, detail="asset not found")
        try:
            scan_key = ScanBindingService.normalize_scan_key(scan_raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="扫码内容不能为空") from exc

        existing = db.query(AssetScanBinding).filter(AssetScanBinding.scan_key == scan_key, AssetScanBinding.status == "active").first()
        if existing and existing.asset_id != asset_id and not force:
            raise HTTPException(status_code=409, detail=f"该扫码内容已绑定资产 {existing.asset_id}，勾选允许重新绑定后再保存")

        action = "bind_scan_code"
        row = existing
        if row:
            action = "rebind_scan_code" if row.asset_id != asset_id else "update_scan_code"
            row.asset_id = asset_id
            row.scan_raw = scan_raw.strip()
            row.scan_type = (scan_type or "generic").strip() or "generic"
            row.remark = remark
            row.updated_at = datetime.utcnow()
        else:
            row = AssetScanBinding(
                asset_id=asset_id,
                scan_key=scan_key,
                scan_raw=scan_raw.strip(),
                scan_type=(scan_type or "generic").strip() or "generic",
                remark=remark,
                created_by=operator,
            )
            db.add(row)
        AuditLogService.record_operation(db, "asset", action, operator, "asset_scan_binding", asset_id, f"扫码绑定 {asset_id}", ScanBindingService.to_out(row))
        db.commit()
        db.refresh(row)
        return ScanBindingService.to_out(row)

    @staticmethod
    def unbind(db: Session, binding_id: int, operator: str, user_context: dict | None) -> dict:
        row = db.get(AssetScanBinding, binding_id)
        if not row or row.status != "active":
            raise HTTPException(status_code=404, detail="scan binding not found")
        if not ScanBindingService.can_access_asset(db, row.asset_id, user_context):
            raise HTTPException(status_code=404, detail="scan binding not found")
        row.status = "deleted"
        row.updated_at = datetime.utcnow()
        AuditLogService.record_operation(db, "asset", "delete_scan_code", operator, "asset_scan_binding", row.asset_id, f"解绑扫码 {row.asset_id}", ScanBindingService.to_out(row))
        db.commit()
        return {"ok": True}

    @staticmethod
    def resolve(db: Session, scan_raw: str, user_context: dict | None) -> dict:
        try:
            scan_key = ScanBindingService.normalize_scan_key(scan_raw)
        except ValueError:
            return {"bound": False, "scan_key": ""}
        row = db.query(AssetScanBinding).filter(AssetScanBinding.scan_key == scan_key, AssetScanBinding.status == "active").first()
        if not row:
            return {"bound": False, "scan_key": scan_key}
        asset = ScanBindingService.can_access_asset(db, row.asset_id, user_context)
        if not asset:
            return {"bound": False, "scan_key": scan_key}
        user = AssetService.users_by_identity(db).get(asset.owner_user_id or "")
        return {"bound": True, "scan_key": scan_key, "asset": AssetService.to_out(asset, user), "binding": ScanBindingService.to_out(row)}
