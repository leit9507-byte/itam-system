from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
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
def list_scrap_requests(page: int = 1, page_size: int = 20, status: str | None = None, db: Session = Depends(get_db)):
    return ScrapService.list_requests(db, page, page_size, status)


@router.post("/{asset_id}/create")
def create_scrap_request(asset_id: str, payload: ScrapPayload, db: Session = Depends(get_db)):
    try:
        return ScrapService.create_request(db, asset_id, payload.model_dump(), payload.operator)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{request_id}/approve")
def approve_scrap_request(request_id: int, payload: ScrapApprovePayload, db: Session = Depends(get_db)):
    try:
        return ScrapService.approve(db, request_id, payload.approver)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{request_id}/reject")
def reject_scrap_request(request_id: int, payload: ScrapApprovePayload, db: Session = Depends(get_db)):
    try:
        return ScrapService.reject(db, request_id, payload.approver)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
