from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.schemas.asset import AssetOut
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseCreate, PurchaseOut, PurchaseReceive
from app.services.purchase_service import PurchaseService


router = APIRouter(prefix="/purchase", tags=["Purchase"])


@router.get("/list")
def list_purchases(
    created_from: date | None = None,
    created_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
    request: Request = None,
    db: Session = Depends(get_db),
):
    start = datetime.combine(created_from, time.min) if created_from else None
    end = datetime.combine(created_to, time.max) if created_to else None
    result = PurchaseService.list_purchases(db, start, end, page, page_size, user_context_from_request(request))
    return {
        **result,
        "list": [PurchaseOut.model_validate(row) for row in result["list"]],
    }


@router.post("/create", response_model=PurchaseOut)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db)):
    return PurchaseService.create_purchase(db, payload)


@router.post("/receive")
def receive_purchase(request: Request, purchase_no: str, payload: PurchaseReceive | None = None, db: Session = Depends(get_db)):
    try:
        result = PurchaseService.receive_purchase(db, purchase_no, operator_from_request(request))
        return {
            "purchase": PurchaseOut.model_validate(result["purchase"]),
            "assets": [AssetOut.model_validate(asset) for asset in result["assets"]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accept")
def accept_purchase(purchase_no: str, payload: PurchaseAcceptanceReceive, request: Request, db: Session = Depends(get_db)):
    try:
        result = PurchaseService.accept_purchase(db, purchase_no, payload.model_copy(update={"operator": operator_from_request(request)}))
        return {
            "purchase": PurchaseOut.model_validate(result["purchase"]),
            "assets": [AssetOut.model_validate(asset) for asset in result["assets"]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
