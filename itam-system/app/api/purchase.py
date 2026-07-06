from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request, user_context_from_request
from app.models.purchase import Purchase
from app.services.approval_service import ApprovalService
from app.schemas.asset import AssetOut
from app.schemas.purchase import PurchaseAcceptanceReceive, PurchaseApprove, PurchaseCreate, PurchaseOut, PurchaseReceive
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


@router.post("/{purchase_no}/approve", response_model=PurchaseOut)
def approve_purchase(request: Request, purchase_no: str, payload: PurchaseApprove | None = None, db: Session = Depends(get_db)):
    try:
        purchase = db.query(Purchase).filter(Purchase.purchase_no == purchase_no).first()
        dept_id = next((item.dept_id for item in purchase.items if item.dept_id), None) if purchase else None
        config = ApprovalService.match_config(db, "purchase", purchase.total_amount if purchase else 0, dept_id)
        if config and purchase:
            PurchaseService.mark_approval_submitted(db, purchase_no, operator_from_request(request))
            ApprovalService.submit_feishu_approval(
                db,
                "purchase",
                purchase_no,
                purchase.total_amount or 0,
                dept_id,
                form={
                    "purchase_no": purchase.purchase_no,
                    "supplier_name": purchase.supplier_name or "",
                    "total_amount": purchase.total_amount or 0,
                    "reason": purchase.purchase_reason or "",
                },
                requester=operator_from_request(request),
            )
            return purchase
        return PurchaseService.approve_purchase(db, purchase_no, operator_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
