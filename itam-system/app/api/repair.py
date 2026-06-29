from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.schemas.repair import RepairCreate, RepairFinish, RepairOut
from app.services.repair_service import RepairService


router = APIRouter(prefix="/repair", tags=["Repair"])


@router.get("/list")
def list_repairs(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    start = datetime.combine(datetime.fromisoformat(start_date).date(), time.min) if start_date else None
    end = datetime.combine(datetime.fromisoformat(end_date).date(), time.max) if end_date else None
    return RepairService.list_records(db, page, page_size, keyword, status, start, end)


@router.post("/create", response_model=RepairOut)
def create_repair(payload: RepairCreate, request: Request, db: Session = Depends(get_db)):
    try:
        return RepairService.create_record(db, payload.model_copy(update={"operator": operator_from_request(request)}))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{record_id}/finish", response_model=RepairOut)
def finish_repair(record_id: int, payload: RepairFinish, request: Request, db: Session = Depends(get_db)):
    try:
        return RepairService.finish_record(db, record_id, payload.model_copy(update={"operator": operator_from_request(request)}))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
