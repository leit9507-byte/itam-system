from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset import AssetBatchImport, AssetCreate, AssetImportResult, AssetOut, AssetStatusChange, AssetTextImport, AssetUpdate
from app.services.asset_service import AssetService


router = APIRouter(prefix="/asset", tags=["Asset"])


@router.post("/create", response_model=AssetOut)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    return AssetService.create_asset(db, payload)


@router.get("/list", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db)):
    return AssetService.list_assets(db)


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetUpdate, db: Session = Depends(get_db)):
    try:
        return AssetService.update_asset(db, asset_id, payload, "asset-manager")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import", response_model=AssetImportResult)
def import_assets(payload: AssetBatchImport, db: Session = Depends(get_db)):
    return AssetService.import_assets(db, payload)


@router.post("/import/text", response_model=AssetImportResult)
def import_assets_from_text(payload: AssetTextImport, db: Session = Depends(get_db)):
    return AssetService.import_assets_from_text(db, payload)


@router.post("/import/excel", response_model=AssetImportResult)
async def import_assets_from_excel(operator: str = "asset-import", file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="please upload .xlsx or .xlsm file")
    try:
        return AssetService.import_assets_from_excel(db, await file.read(), operator)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid excel file: {exc}") from exc


@router.post("/{asset_id}/status", response_model=AssetOut)
def change_asset_status(asset_id: str, payload: AssetStatusChange, db: Session = Depends(get_db)):
    try:
        return AssetService.change_status(
            db,
            asset_id,
            payload.to_status,
            payload.operator,
            payload.owner_user_id,
            payload.dept_id,
            payload.location,
            payload.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
