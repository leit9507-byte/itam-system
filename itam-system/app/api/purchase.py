from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.asset import AssetOut
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseCreate, PurchaseOut, PurchaseReceive
from app.services.purchase_service import PurchaseService


router = APIRouter(prefix="/purchase", tags=["Purchase"])


@router.get("/list", response_model=list[PurchaseOut])
def list_purchases(db: Session = Depends(get_db)):
    return PurchaseService.list_purchases(db)


@router.post("/create", response_model=PurchaseOut)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db)):
    return PurchaseService.create_purchase(db, payload)


@router.post("/receive")
def receive_purchase(purchase_no: str, payload: PurchaseReceive | None = None, db: Session = Depends(get_db)):
    try:
        result = PurchaseService.receive_purchase(db, purchase_no, payload.operator if payload else "system")
        return {
            "purchase": PurchaseOut.model_validate(result["purchase"]),
            "assets": [AssetOut.model_validate(asset) for asset in result["assets"]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accept")
def accept_purchase(purchase_no: str, payload: PurchaseAcceptanceReceive, db: Session = Depends(get_db)):
    try:
        result = PurchaseService.accept_purchase(db, purchase_no, payload)
        return {
            "purchase": PurchaseOut.model_validate(result["purchase"]),
            "assets": [AssetOut.model_validate(asset) for asset in result["assets"]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
