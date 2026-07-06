from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.services.approval_service import ApprovalService
from app.services.scrap_service import ScrapService


router = APIRouter(prefix="/scrap", tags=["Scrap"])


class ScrapPayload(BaseModel):
    applicant: str | None = None
    reason: str | None = None
    disposal_method: str | None = None
    estimated_residual_value: float = 0
    operator: str = "资产管理员"


class ScrapApprovePayload(BaseModel):
    approver: str = "资产负责人"


@router.get("/list")
def list_scrap_requests(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    start = datetime.combine(created_from, time.min) if created_from else None
    end = datetime.combine(created_to, time.max) if created_to else None
    return ScrapService.list_requests(db, page, page_size, status, start, end, user_context_from_request(request))


@router.post("/{asset_id}/create")
def create_scrap_request(asset_id: str, payload: ScrapPayload, request: Request, db: Session = Depends(get_db)):
    try:
        row = ScrapService.create_request(db, asset_id, payload.model_dump(), operator_from_request(request))
        config = ApprovalService.match_config(db, "scrap", row.purchase_price or 0, row.dept_id)
        if config:
            ApprovalService.submit_feishu_approval(
                db,
                "scrap",
                row.request_no,
                row.purchase_price or 0,
                row.dept_id,
                form={
                    "request_no": row.request_no,
                    "asset_id": row.asset_id,
                    "asset_name": row.asset_name,
                    "reason": row.reason or "",
                    "residual_value": row.estimated_residual_value or 0,
                },
                requester=operator_from_request(request),
            )
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{request_id}/approve")
def approve_scrap_request(request_id: int, payload: ScrapApprovePayload, request: Request, db: Session = Depends(get_db)):
    try:
        return ScrapService.approve(db, request_id, operator_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{request_id}/reject")
def reject_scrap_request(request_id: int, payload: ScrapApprovePayload, request: Request, db: Session = Depends(get_db)):
    try:
        return ScrapService.reject(db, request_id, operator_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
