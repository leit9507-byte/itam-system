from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.scrap import ScrapRequest
from app.services.scrap_service import ScrapService


router = APIRouter(prefix="/scrap", tags=["Scrap"])


class ScrapPayload(BaseModel):
    applicant: str | None = None
    reason: str | None = None
    disposal_method: str | None = None
    retirement_date: datetime | None = None
    retirement_approval_no: str | None = None
    estimated_residual_value: float = 0
    operator: str = "资产管理员"


class ScrapDisposePayload(BaseModel):
    final_residual_value: float = 0
    disposal_method: str | None = None
    retirement_date: datetime | None = None
    retirement_approval_no: str | None = None
    dispose_recipient_user_id: str | None = None
    dispose_recipient_name: str | None = None
    disposal_remark: str | None = None


class ScrapBatchDisposePayload(ScrapDisposePayload):
    request_ids: list[int] = Field(default_factory=list)
    final_residual_value_mode: str | None = None


@router.get("/list")
def list_scrap_requests(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    asset_id: str | None = None,
    disposal_method: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    start = datetime.combine(created_from, time.min) if created_from else None
    end = datetime.combine(created_to, time.max) if created_to else None
    return ScrapService.list_requests(
        db,
        page=page,
        page_size=page_size,
        status=status,
        asset_id=asset_id,
        created_from=start,
        created_to=end,
        user_context=user_context_from_request(request),
        disposal_method=disposal_method,
    )


@router.post("/{asset_id}/create")
def create_scrap_request(asset_id: str, payload: ScrapPayload, request: Request, db: Session = Depends(get_db)):
    try:
        row = ScrapService.create_request(db, asset_id, payload.model_dump(), operator_from_request(request), user_context_from_request(request))
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{request_id}/dispose")
def dispose_scrap_request(request_id: int, payload: ScrapDisposePayload, request: Request, db: Session = Depends(get_db)):
    try:
        return ScrapService.dispose(db, request_id, payload.model_dump(), operator_from_request(request), user_context_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch-dispose")
def batch_dispose_scrap_requests(payload: ScrapBatchDisposePayload, request: Request, db: Session = Depends(get_db)):
    request_ids = list(dict.fromkeys([item for item in payload.request_ids if item]))
    if not request_ids:
        raise HTTPException(status_code=400, detail="请选择需要退役登记的资产")
    data = payload.model_dump(exclude={"request_ids"})
    user_context = user_context_from_request(request)
    operator = operator_from_request(request)
    residual_values = {}
    if data.pop("final_residual_value_mode", "") == "total":
        total_value = float(data.get("final_residual_value") or 0)
        scoped_rows = ScrapService.apply_data_scope(
            db.query(ScrapRequest).filter(ScrapRequest.id.in_(request_ids)),
            user_context,
        ).all()
        row_map = {row.id: row for row in scoped_rows}
        weights = [max(float(row_map[request_id].estimated_residual_value or 0), 0) if request_id in row_map else 0 for request_id in request_ids]
        weight_total = sum(weights)
        remaining = total_value
        for index, request_id in enumerate(request_ids):
            if index == len(request_ids) - 1:
                residual_values[request_id] = round(remaining, 2)
                break
            if weight_total > 0:
                value = round(total_value * (weights[index] / weight_total), 2)
            else:
                value = round(total_value / len(request_ids), 2)
            residual_values[request_id] = value
            remaining -= value
    rows = []
    errors = []
    for request_id in request_ids:
        try:
            item_data = dict(data)
            if request_id in residual_values:
                item_data["final_residual_value"] = residual_values[request_id]
            row = ScrapService.dispose(db, request_id, item_data, operator, user_context)
            rows.append(row)
        except ValueError as exc:
            errors.append({"request_id": request_id, "message": str(exc)})
    return {"success": len(rows), "failed": len(errors), "list": rows, "errors": errors}
