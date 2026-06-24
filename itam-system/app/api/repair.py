from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.repair import RepairCreate, RepairFinish, RepairOut
from app.services.repair_service import RepairService


router = APIRouter(prefix="/repair", tags=["Repair"])


@router.get("/list", response_model=list[RepairOut])
def list_repairs(db: Session = Depends(get_db)):
    return RepairService.list_records(db)


@router.post("/create", response_model=RepairOut)
def create_repair(payload: RepairCreate, db: Session = Depends(get_db)):
    try:
        return RepairService.create_record(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{record_id}/finish", response_model=RepairOut)
def finish_repair(record_id: int, payload: RepairFinish, db: Session = Depends(get_db)):
    try:
        return RepairService.finish_record(db, record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
