from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.inventory import InventoryItem, InventoryLedger
from app.schemas.inventory import InventoryItemCreate, InventoryItemOut, InventoryItemUpdate, InventoryLedgerCreate, InventoryLedgerOut


router = APIRouter(prefix="/inventory", tags=["Inventory"])

VALID_TYPES = {"license", "consumable", "accessory", "component"}
ASSIGN_ACTIONS = {"assign", "consume", "install"}
RETURN_ACTIONS = {"return", "uninstall"}


@router.get("/items")
def list_items(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    item_type: str | None = None,
    item_types: str | None = None,
    status: str | None = None,
    low_stock: bool = False,
    expiring_days: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(InventoryItem)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(InventoryItem.code.like(pattern), InventoryItem.name.like(pattern), InventoryItem.brand.like(pattern), InventoryItem.model.like(pattern), InventoryItem.supplier.like(pattern)))
    if item_type:
        validate_type(item_type)
        query = query.filter(InventoryItem.item_type == item_type)
    elif item_types:
        type_values = [value.strip() for value in item_types.split(",") if value.strip()]
        for value in type_values:
            validate_type(value)
        if type_values:
            query = query.filter(InventoryItem.item_type.in_(type_values))
    if status:
        query = query.filter(InventoryItem.status == status)
    if low_stock:
        query = query.filter(InventoryItem.available_qty <= InventoryItem.min_qty)
    if expiring_days is not None:
        from datetime import datetime, timedelta

        query = query.filter(InventoryItem.expire_date.isnot(None), InventoryItem.expire_date <= datetime.utcnow() + timedelta(days=max(expiring_days, 0)))
    total = query.count()
    page = max(page, 1)
    page_size = min(max(page_size or 20, 1), 200)
    rows = query.order_by(InventoryItem.updated_at.desc(), InventoryItem.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summary = build_summary(db, item_type=item_type, item_types=item_types)
    return {"list": rows, "total": total, "page": page, "page_size": page_size, "summary": summary}


@router.post("/items", response_model=InventoryItemOut)
def create_item(payload: InventoryItemCreate, request: Request, db: Session = Depends(get_db)):
    validate_type(payload.item_type)
    if db.query(InventoryItem).filter(InventoryItem.code == payload.code).first():
        raise HTTPException(status_code=409, detail="编码已存在")
    available_qty = payload.available_qty if payload.available_qty is not None else payload.total_qty
    item = InventoryItem(**payload.model_dump(exclude={"available_qty"}), available_qty=available_qty, assigned_qty=max(payload.total_qty - available_qty, 0))
    db.add(item)
    db.flush()
    add_ledger(db, item, InventoryLedgerCreate(action="create", quantity=item.total_qty, location=item.location, remark=payload.remark), operator_from_request(request))
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=InventoryItemOut)
def update_item(item_id: int, payload: InventoryItemUpdate, db: Session = Depends(get_db)):
    item = require_item(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "item_type" in data:
        validate_type(data["item_type"])
    if "code" in data and db.query(InventoryItem).filter(InventoryItem.code == data["code"], InventoryItem.id != item_id).first():
        raise HTTPException(status_code=409, detail="编码已存在")
    for key, value in data.items():
        setattr(item, key, value)
    item.assigned_qty = max((item.total_qty or 0) - (item.available_qty or 0), 0)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items/{item_id}/ledger", response_model=list[InventoryLedgerOut])
def item_ledger(item_id: int, limit: int = 200, db: Session = Depends(get_db)):
    return db.query(InventoryLedger).filter(InventoryLedger.item_id == item_id).order_by(InventoryLedger.created_at.desc(), InventoryLedger.id.desc()).limit(min(max(limit, 1), 500)).all()


@router.post("/items/{item_id}/ledger", response_model=InventoryItemOut)
def operate_item(item_id: int, payload: InventoryLedgerCreate, request: Request, db: Session = Depends(get_db)):
    item = require_item(db, item_id)
    quantity = max(int(payload.quantity or 1), 1)
    action = payload.action
    if action in {"in", "adjust_add"}:
        item.total_qty += quantity
        item.available_qty += quantity
    elif action in {"out", "adjust_sub"}:
        ensure_available(item, quantity)
        item.total_qty -= quantity
        item.available_qty -= quantity
    elif action in ASSIGN_ACTIONS:
        ensure_available(item, quantity)
        item.available_qty -= quantity
        item.assigned_qty += quantity
    elif action in RETURN_ACTIONS:
        item.available_qty += quantity
        item.assigned_qty = max(item.assigned_qty - quantity, 0)
    else:
        raise HTTPException(status_code=400, detail="不支持的库存操作")
    add_ledger(db, item, payload, operator_from_request(request))
    db.commit()
    db.refresh(item)
    return item


def require_item(db: Session, item_id: int) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="库存对象不存在")
    return item


def validate_type(item_type: str) -> None:
    if item_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="类型只能是 license、consumable、accessory、component")


def ensure_available(item: InventoryItem, quantity: int) -> None:
    if item.available_qty < quantity:
        raise HTTPException(status_code=400, detail="可用库存不足")


def add_ledger(db: Session, item: InventoryItem, payload: InventoryLedgerCreate, operator: str) -> None:
    db.add(InventoryLedger(item_id=item.id, operator=operator, **payload.model_dump()))


def build_summary(db: Session, item_type: str | None = None, item_types: str | None = None) -> dict:
    from datetime import datetime, timedelta

    query = db.query(InventoryItem)
    if item_type:
        query = query.filter(InventoryItem.item_type == item_type)
    elif item_types:
        type_values = [value.strip() for value in item_types.split(",") if value.strip()]
        if type_values:
            query = query.filter(InventoryItem.item_type.in_(type_values))
    rows = query.all()
    expiring_deadline = datetime.utcnow() + timedelta(days=90)
    return {
        "total": len(rows),
        "license": sum(1 for item in rows if item.item_type == "license"),
        "consumable": sum(1 for item in rows if item.item_type == "consumable"),
        "accessory": sum(1 for item in rows if item.item_type == "accessory"),
        "component": sum(1 for item in rows if item.item_type == "component"),
        "low_stock": sum(1 for item in rows if item.available_qty <= item.min_qty),
        "assigned_qty": sum(item.assigned_qty or 0 for item in rows),
        "total_available_qty": sum(item.available_qty or 0 for item in rows),
        "expiring": sum(1 for item in rows if item.expire_date and item.expire_date <= expiring_deadline),
    }
