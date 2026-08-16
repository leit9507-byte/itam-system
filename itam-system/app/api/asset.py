from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.asset import Asset
from app.schemas.asset import AssetBatchCheckinCreate, AssetBatchCheckoutCreate, AssetBatchImport, AssetBatchRepairCreate, AssetBatchUpdateCreate, AssetCheckinCreate, AssetCheckoutCreate, AssetCheckoutOut, AssetCreate, AssetImportResult, AssetOut, AssetStatusChange, AssetTextImport, AssetUpdate
from app.schemas.repair import RepairCreate
from app.services.asset_service import AssetService, AssetValidationError
from app.services.repair_service import RepairService
from app.services.todo_service import TodoService


router = APIRouter(prefix="/asset", tags=["Asset"])


@router.post("/create", response_model=AssetOut)
def create_asset(payload: AssetCreate, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetService.create_asset(db, payload, operator_from_request(request), user_context_from_request(request))
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        # 并发创建同名资产/序列号时兜底，避免 500
        raise HTTPException(status_code=409, detail="资产编号或序列号已存在，请刷新后重试") from exc


@router.get("/list")
def list_assets(
    page: int = 1,
    page_size: int = 0,
    keyword: str | None = None,
    status: str | None = None,
    category: str | None = None,
    company: str | None = None,
    supplier: str | None = None,
    owner_user_id: str | None = None,
    risk_filter: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    return AssetService.list_assets(
        db,
        page,
        page_size,
        keyword,
        status,
        category,
        company,
        supplier,
        user_context_from_request(request),
        risk_filter,
        owner_user_id,
    )


@router.get("/summary")
def asset_summary(request: Request, db: Session = Depends(get_db)):
    return AssetService.asset_summary(db, user_context_from_request(request))


@router.get("/checkouts/list")
def list_asset_checkouts(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    checkout_type: str | None = None,
    assignee_user_id: str | None = None,
    dept_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    due_days: int = 7,
    db: Session = Depends(get_db),
):
    return AssetService.list_checkout_records(
        db,
        page,
        page_size,
        keyword,
        status,
        checkout_type,
        assignee_user_id,
        dept_id,
        date_from,
        date_to,
        due_from,
        due_to,
        due_days,
        user_context_from_request(request),
    )


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetService.get_asset(db, asset_id, user_context_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/checkouts/batch-checkout")
def batch_checkout_assets(payload: AssetBatchCheckoutCreate, request: Request, db: Session = Depends(get_db)):
    result = AssetService.batch_checkout_assets(db, payload, operator_from_request(request), user_context_from_request(request))
    TodoService.invalidate()
    return result


@router.post("/batch-outbound")
def batch_outbound_assets(payload: AssetBatchCheckoutCreate, request: Request, db: Session = Depends(get_db)):
    result = AssetService.batch_checkout_assets(db, payload, operator_from_request(request), user_context_from_request(request))
    TodoService.invalidate()
    return result


@router.post("/checkouts/batch-checkin")
def batch_checkin_assets(payload: AssetBatchCheckinCreate, request: Request, db: Session = Depends(get_db)):
    result = AssetService.batch_checkin_assets(db, payload, operator_from_request(request), user_context_from_request(request))
    TodoService.invalidate()
    return result


@router.post("/batch-inbound")
def batch_inbound_assets(payload: AssetBatchCheckinCreate, request: Request, db: Session = Depends(get_db)):
    result = AssetService.batch_checkin_assets(db, payload, operator_from_request(request), user_context_from_request(request))
    TodoService.invalidate()
    return result


@router.post("/batch-update")
def batch_update_assets(payload: AssetBatchUpdateCreate, request: Request, db: Session = Depends(get_db)):
    return AssetService.batch_update_assets(db, payload, operator_from_request(request), user_context_from_request(request))


@router.post("/batch-repair")
def batch_repair_assets(payload: AssetBatchRepairCreate, request: Request, db: Session = Depends(get_db)):
    rows = []
    errors = []
    operator = operator_from_request(request)
    user_context = user_context_from_request(request)
    for asset_id in dict.fromkeys([item for item in payload.asset_ids if item]):
        try:
            repair_payload = RepairCreate(
                asset_id=asset_id,
                repair_time=payload.repair_time,
                repair_type=payload.repair_type,
                fault_reason=payload.fault_reason,
                repair_cost=payload.repair_cost,
                vendor=payload.vendor,
                operator=operator,
                remark=payload.remark,
            )
            rows.append(RepairService.create_record(db, repair_payload, user_context))
        except ValueError as exc:
            db.rollback()
            errors.append({"asset_id": asset_id, "message": str(exc)})
    return {"success": len(rows), "failed": len(errors), "repairs": rows, "errors": errors}


@router.get("/{asset_id}/changes")
def asset_changes(asset_id: str, request: Request, limit: int = 200, db: Session = Depends(get_db)):
    return AssetService.list_asset_changes(db, asset_id, limit, user_context_from_request(request))


@router.get("/{asset_id}/checkouts", response_model=list[AssetCheckoutOut])
def asset_checkouts(asset_id: str, request: Request, limit: int = 200, db: Session = Depends(get_db)):
    return AssetService.list_checkouts(db, asset_id, limit, user_context_from_request(request))


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: str, payload: AssetUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetService.update_asset(db, asset_id, payload, operator_from_request(request), user_context_from_request(request))
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import", response_model=AssetImportResult)
def import_assets(payload: AssetBatchImport, request: Request, db: Session = Depends(get_db)):
    return AssetService.import_assets(db, payload.model_copy(update={"operator": operator_from_request(request)}), user_context_from_request(request))


@router.post("/import/text", response_model=AssetImportResult)
def import_assets_from_text(payload: AssetTextImport, request: Request, db: Session = Depends(get_db)):
    return AssetService.import_assets_from_text(db, payload.model_copy(update={"operator": operator_from_request(request)}), user_context_from_request(request))


@router.post("/import/text/preview")
def preview_assets_from_text(payload: AssetTextImport, db: Session = Depends(get_db)):
    return AssetService.preview_import_text(db, payload)


@router.post("/import/excel", response_model=AssetImportResult)
async def import_assets_from_excel(request: Request, operator: str = "asset-import", overwrite: bool = False, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xlsm 格式的 Excel 文件")
    content = await file.read()
    enforce_import_size(content)
    try:
        return AssetService.import_assets_from_excel(
            db, content, operator_from_request(request), overwrite=overwrite,
            user_context=user_context_from_request(request),
        )
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 导入失败：{exc}") from exc


@router.post("/import/excel/preview")
async def preview_assets_from_excel(overwrite: bool = False, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xlsm 格式的 Excel 文件")
    content = await file.read()
    enforce_import_size(content)
    try:
        return AssetService.preview_import_excel(db, content, overwrite=overwrite)
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 预览失败：{exc}") from exc


def enforce_import_size(content: bytes) -> None:
    """Excel 导入限制为上传上限的 3 倍，防止超大文件耗尽内存导致服务崩溃。"""
    limit = get_settings().max_upload_size_mb * 1024 * 1024 * 3
    if len(content) > limit:
        raise HTTPException(status_code=413, detail=f"Excel 文件过大，最大 {limit // (1024 * 1024)} MB")


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
        result = AssetService.change_status(
            db,
            asset_id,
            payload.to_status,
            operator_from_request(request),
            payload.owner_user_id,
            payload.dept_id,
            payload.location,
            payload.borrow_due_date,
            payload.remark,
            user_context_from_request(request),
        )
        TodoService.invalidate()
        return result
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{asset_id}/checkout", response_model=AssetOut)
def checkout_asset(asset_id: str, payload: AssetCheckoutCreate, request: Request, db: Session = Depends(get_db)):
    try:
        result = AssetService.checkout_asset(db, asset_id, payload, operator_from_request(request), user_context_from_request(request))
        TodoService.invalidate()
        return result
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{asset_id}/checkin", response_model=AssetOut)
def checkin_asset(asset_id: str, payload: AssetCheckinCreate, request: Request, db: Session = Depends(get_db)):
    try:
        result = AssetService.checkin_asset(db, asset_id, payload, operator_from_request(request), user_context_from_request(request))
        TodoService.invalidate()
        return result
    except AssetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
