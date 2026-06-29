from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset import AssetBatchImport, AssetCreate, AssetImportResult, AssetOut, AssetStatusChange, AssetTextImport, AssetUpdate
from app.services.asset_service import AssetService, AssetValidationError


router = APIRouter(prefix="/asset", tags=["Asset"])


@router.post("/create", response_model=AssetOut)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    return AssetService.create_asset(db, payload)


@router.get("/list")
def list_assets(
    page: int = 1,
    page_size: int = 0,
    keyword: str | None = None,
    status: str | None = None,
    category: str | None = None,
    company: str | None = None,
    supplier: str | None = None,
    db: Session = Depends(get_db),
):
    return AssetService.list_assets(db, page, page_size, keyword, status, category, company, supplier)


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetUpdate, db: Session = Depends(get_db)):
    try:
        return AssetService.update_asset(db, asset_id, payload, "asset-manager")
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import", response_model=AssetImportResult)
def import_assets(payload: AssetBatchImport, db: Session = Depends(get_db)):
    return AssetService.import_assets(db, payload)


@router.post("/import/text", response_model=AssetImportResult)
def import_assets_from_text(payload: AssetTextImport, db: Session = Depends(get_db)):
    return AssetService.import_assets_from_text(db, payload)


@router.post("/import/text/preview")
def preview_assets_from_text(payload: AssetTextImport, db: Session = Depends(get_db)):
    return AssetService.preview_import_text(db, payload)


@router.post("/import/excel", response_model=AssetImportResult)
async def import_assets_from_excel(operator: str = "asset-import", file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xlsm 格式的 Excel 文件")
    try:
        return AssetService.import_assets_from_excel(db, await file.read(), operator)
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 导入失败：{exc}") from exc


@router.post("/import/excel/preview")
async def preview_assets_from_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xlsm 格式的 Excel 文件")
    try:
        return AssetService.preview_import_excel(db, await file.read())
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 预览失败：{exc}") from exc


@router.get("/import/template")
def download_asset_import_template():
    content = AssetService.build_import_template()
    headers = {"Content-Disposition": 'attachment; filename="asset_import_template.xlsx"'}
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


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
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
