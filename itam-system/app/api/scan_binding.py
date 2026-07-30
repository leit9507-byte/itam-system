from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.time import TimezoneModel
from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.services.feishu_jsapi_service import FeishuJsapiService
from app.services.scan_binding_service import ScanBindingService


router = APIRouter(prefix="/scan-bindings", tags=["ScanBinding"])


class ScanBindPayload(TimezoneModel):
    scan_raw: str
    scan_type: str | None = "generic"
    remark: str | None = None
    force: bool = False


class ScanResolvePayload(TimezoneModel):
    scan_raw: str


@router.get("/asset/{asset_id}")
def list_asset_scan_bindings(asset_id: str, request: Request, db: Session = Depends(get_db)):
    return ScanBindingService.list_for_asset(db, asset_id, user_context_from_request(request))


@router.post("/asset/{asset_id}")
def bind_asset_scan_code(asset_id: str, payload: ScanBindPayload, request: Request, db: Session = Depends(get_db)):
    return ScanBindingService.bind_to_asset(
        db,
        asset_id,
        payload.scan_raw,
        payload.scan_type or "generic",
        payload.remark,
        payload.force,
        operator_from_request(request),
        user_context_from_request(request),
    )


@router.delete("/{binding_id}")
def delete_scan_binding(binding_id: int, request: Request, db: Session = Depends(get_db)):
    return ScanBindingService.unbind(db, binding_id, operator_from_request(request), user_context_from_request(request))


@router.post("/{binding_id}/unbind")
def unbind_scan_binding(binding_id: int, request: Request, db: Session = Depends(get_db)):
    return ScanBindingService.unbind(db, binding_id, operator_from_request(request), user_context_from_request(request))


@router.post("/resolve")
def resolve_scan_code(payload: ScanResolvePayload, request: Request, db: Session = Depends(get_db)):
    return ScanBindingService.resolve(db, payload.scan_raw, user_context_from_request(request))


@router.get("/feishu-jsapi-signature")
def feishu_jsapi_signature(url: str, db: Session = Depends(get_db)):
    try:
        return FeishuJsapiService.build_signature(db, url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
