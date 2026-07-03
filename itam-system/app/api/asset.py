from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.schemas.asset import AssetBatchImport, AssetCreate, AssetImportResult, AssetOut, AssetStatusChange, AssetTextImport, AssetUpdate
from app.services.asset_service import AssetService, AssetValidationError


router = APIRouter(prefix="/asset", tags=["Asset"])


@router.post("/create", response_model=AssetOut)
def create_asset(payload: AssetCreate, request: Request, db: Session = Depends(get_db)):
    return AssetService.create_asset(db, payload, operator_from_request(request))


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


@router.get("/summary")
def asset_summary(db: Session = Depends(get_db)):
    return AssetService.asset_summary(db)


@router.get("/{asset_id}/changes")
def asset_changes(asset_id: str, limit: int = 200, db: Session = Depends(get_db)):
    return AssetService.list_asset_changes(db, asset_id, limit)


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetService.update_asset(db, asset_id, payload, operator_from_request(request))
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import", response_model=AssetImportResult)
def import_assets(payload: AssetBatchImport, request: Request, db: Session = Depends(get_db)):
    return AssetService.import_assets(db, payload.model_copy(update={"operator": operator_from_request(request)}))


@router.post("/import/text", response_model=AssetImportResult)
def import_assets_from_text(payload: AssetTextImport, request: Request, db: Session = Depends(get_db)):
    return AssetService.import_assets_from_text(db, payload.model_copy(update={"operator": operator_from_request(request)}))


@router.post("/import/text/preview")
def preview_assets_from_text(payload: AssetTextImport, db: Session = Depends(get_db)):
    return AssetService.preview_import_text(db, payload)


@router.post("/import/excel", response_model=AssetImportResult)
async def import_assets_from_excel(request: Request, operator: str = "asset-import", file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xlsm 格式的 Excel 文件")
    try:
        return AssetService.import_assets_from_excel(db, await file.read(), operator_from_request(request))
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
def change_asset_status(asset_id: str, payload: AssetStatusChange, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetService.change_status(
            db,
            asset_id,
            payload.to_status,
            operator_from_request(request),
            payload.owner_user_id,
            payload.dept_id,
            payload.location,
            payload.remark,
        )
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
