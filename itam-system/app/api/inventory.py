from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.core.database import get_db
from app.core.security import can_view_all_data, is_department_manager, operator_from_request, scoped_dept_id, scoped_user_identities, user_context_from_request
from app.models.asset import Asset
from app.models.inventory import InventoryComponentInstallation, InventoryItem, InventoryLedger, InventoryLicenseSeat, InventoryLicenseSeatHistory
from app.models.user import UserDirectory
from app.schemas.inventory import ComponentInstallationPage, InventoryItemCreate, InventoryItemOut, InventoryItemUpdate, InventoryLedgerCreate, InventoryLedgerOut, LicenseSeatAssign, LicenseSeatBatchCreate, LicenseSeatHistoryOut, LicenseSeatOut, LicenseSeatPage, LicenseSeatReturn
from app.services.asset_service import AssetService


router = APIRouter(prefix="/inventory", tags=["Inventory"])

VALID_TYPES = {"license", "consumable", "accessory", "component"}
ASSIGN_ACTIONS = {"assign", "consume", "install"}
RETURN_ACTIONS = {"return", "uninstall"}


@router.get("/items")
def list_items(
    request: Request,
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
    user_context = user_context_from_request(request)
    query = apply_inventory_scope(db.query(InventoryItem), db, user_context)
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

        query = query.filter(InventoryItem.expire_date.isnot(None), InventoryItem.expire_date <= utc_now() + timedelta(days=max(expiring_days, 0)))
    total = query.count()
    page = max(page, 1)
    page_size = min(max(page_size or 20, 1), 200)
    rows = query.order_by(InventoryItem.updated_at.desc(), InventoryItem.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summary = build_summary(db, user_context, item_type=item_type, item_types=item_types)
    return {"list": rows, "total": total, "page": page, "page_size": page_size, "summary": summary}


@router.get("/assignees")
def list_inventory_assignees(request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    query = db.query(UserDirectory).filter(UserDirectory.status == "active")
    if not can_manage_all_inventory(user_context):
        dept_id = scoped_dept_id(user_context)
        if is_department_manager(user_context) and dept_id:
            query = query.filter((UserDirectory.dept_id == dept_id) | (UserDirectory.dept_name == dept_id))
        else:
            identities = scoped_user_identities(user_context)
            query = query.filter((UserDirectory.user_id.in_(identities)) | (UserDirectory.username.in_(identities))) if identities else query.filter(False)
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "dept_id": user.dept_id or "",
            "dept_name": user.dept_name or "",
        }
        for user in query.order_by(UserDirectory.display_name.asc(), UserDirectory.username.asc()).limit(1000).all()
    ]


@router.post("/items", response_model=InventoryItemOut)
def create_item(payload: InventoryItemCreate, request: Request, db: Session = Depends(get_db)):
    validate_type(payload.item_type)
    if db.query(InventoryItem).filter(InventoryItem.code == payload.code).first():
        raise HTTPException(status_code=409, detail="编码已存在")
    user_context = user_context_from_request(request)
    dept_id = writable_inventory_dept(payload.dept_id, user_context)
    available_qty = payload.total_qty if payload.item_type == "license" else payload.available_qty if payload.available_qty is not None else payload.total_qty
    item = InventoryItem(**payload.model_dump(exclude={"available_qty", "dept_id"}), dept_id=dept_id, available_qty=available_qty, assigned_qty=max(payload.total_qty - available_qty, 0))
    db.add(item)
    db.flush()
    if item.item_type == "license" and item.total_qty:
        add_license_seats(db, item, int(item.total_qty), [], operator_from_request(request), payload.remark)
        sync_license_counts(db, item)
    add_ledger(db, item, InventoryLedgerCreate(action="create", quantity=item.total_qty, dept_id=item.dept_id, location=item.location, remark=payload.remark), operator_from_request(request))
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=InventoryItemOut)
def update_item(item_id: int, payload: InventoryItemUpdate, request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    item = require_item(db, item_id, user_context)
    writable_inventory_dept(item.dept_id, user_context)
    data = payload.model_dump(exclude_unset=True)
    if "item_type" in data:
        validate_type(data["item_type"])
        if data["item_type"] != item.item_type:
            raise HTTPException(status_code=400, detail="库存类型创建后不能修改")
    if "code" in data and db.query(InventoryItem).filter(InventoryItem.code == data["code"], InventoryItem.id != item_id).first():
        raise HTTPException(status_code=409, detail="编码已存在")
    if "dept_id" in data:
        data["dept_id"] = writable_inventory_dept(data["dept_id"], user_context)
    license_total = data.pop("total_qty", None) if item.item_type == "license" else None
    if item.item_type == "license":
        data.pop("available_qty", None)
    for key, value in data.items():
        setattr(item, key, value)
    if item.item_type == "license":
        reconcile_license_seats(db, item, int(license_total if license_total is not None else item.total_qty), operator_from_request(request))
        sync_license_counts(db, item)
    else:
        item.assigned_qty = max((item.total_qty or 0) - (item.available_qty or 0), 0)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items/{item_id}/ledger", response_model=list[InventoryLedgerOut])
def item_ledger(item_id: int, request: Request, limit: int = 200, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    require_item(db, item_id, user_context)
    query = apply_inventory_ledger_scope(db.query(InventoryLedger), user_context)
    return query.filter(InventoryLedger.item_id == item_id).order_by(InventoryLedger.created_at.desc(), InventoryLedger.id.desc()).limit(min(max(limit, 1), 500)).all()


@router.post("/items/{item_id}/ledger", response_model=InventoryItemOut)
def operate_item(item_id: int, payload: InventoryLedgerCreate, request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    item = require_item(db, item_id, user_context)
    writable_inventory_dept(item.dept_id, user_context)
    validate_inventory_targets(db, payload, user_context)
    quantity = max(int(payload.quantity or 1), 1)
    action = payload.action
    if item.item_type == "license" and action in ASSIGN_ACTIONS | RETURN_ACTIONS:
        raise HTTPException(status_code=400, detail="软件许可请在授权席位中执行分配或回收")
    if item.item_type == "license" and action in {"in", "adjust_add", "out", "adjust_sub"}:
        target_total = item.total_qty + quantity if action in {"in", "adjust_add"} else item.total_qty - quantity
        reconcile_license_seats(db, item, target_total, operator_from_request(request), payload.remark)
        sync_license_counts(db, item)
    elif action in {"in", "adjust_add"}:
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
        if item.item_type == "component" and action == "uninstall":
            update_component_installation(db, item, payload, quantity, operator_from_request(request), installing=False)
        item.available_qty += quantity
        item.assigned_qty = max(item.assigned_qty - quantity, 0)
    else:
        raise HTTPException(status_code=400, detail="不支持的库存操作")
    if item.item_type == "component" and action == "install":
        update_component_installation(db, item, payload, quantity, operator_from_request(request), installing=True)
    ledger_payload = payload.model_copy(update={"dept_id": writable_inventory_dept(payload.dept_id or item.dept_id, user_context)})
    add_ledger(db, item, ledger_payload, operator_from_request(request))
    db.commit()
    db.refresh(item)
    return item


@router.get("/items/{item_id}/license-seats", response_model=LicenseSeatPage)
def list_license_seats(item_id: int, request: Request, status: str | None = None, keyword: str | None = None, page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    item = require_typed_item(db, item_id, "license", user_context)
    base_query = apply_license_seat_scope(db.query(InventoryLicenseSeat), user_context).filter(InventoryLicenseSeat.item_id == item.id)
    summary_rows = base_query.with_entities(InventoryLicenseSeat.status).all()
    summary = {key: 0 for key in ["available", "assigned", "recovered", "disabled"]}
    for row in summary_rows:
        summary[row[0]] = summary.get(row[0], 0) + 1
    query = base_query
    if status:
        query = query.filter(InventoryLicenseSeat.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(InventoryLicenseSeat.seat_code.like(pattern), InventoryLicenseSeat.assignee_name.like(pattern), InventoryLicenseSeat.assignee_user_id.like(pattern), InventoryLicenseSeat.asset_id.like(pattern)))
    total = query.count()
    page = max(page, 1)
    page_size = min(max(page_size or 10, 1), 200)
    rows = query.order_by(InventoryLicenseSeat.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size, "summary": summary}


@router.post("/items/{item_id}/license-seats", response_model=list[LicenseSeatOut])
def create_license_seats(item_id: int, payload: LicenseSeatBatchCreate, request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    item = require_typed_item(db, item_id, "license", user_context)
    writable_inventory_dept(item.dept_id, user_context)
    operator = operator_from_request(request)
    seats = add_license_seats(db, item, max(payload.count, len(payload.seat_codes)), payload.seat_codes, operator, payload.remark)
    sync_license_counts(db, item)
    add_ledger(db, item, InventoryLedgerCreate(action="adjust_add", quantity=len(seats), dept_id=item.dept_id, remark=payload.remark or "新增授权席位"), operator)
    db.commit()
    return seats


@router.post("/license-seats/{seat_id}/assign", response_model=LicenseSeatOut)
def assign_license_seat(seat_id: int, payload: LicenseSeatAssign, request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    seat, item = require_license_seat(db, seat_id, user_context)
    writable_inventory_dept(item.dept_id, user_context)
    if seat.status not in {"available", "recovered"}:
        raise HTTPException(status_code=400, detail="只有可用或已回收席位可以分配")
    if not payload.assignee_user_id and not payload.asset_id:
        raise HTTPException(status_code=400, detail="请选择领用人或绑定资产")
    ledger_payload = InventoryLedgerCreate(action="assign", quantity=1, assignee_user_id=payload.assignee_user_id, assignee_name=payload.assignee_name, dept_id=payload.dept_id, asset_id=payload.asset_id, remark=payload.remark)
    validate_inventory_targets(db, ledger_payload, user_context)
    dept_id = resolve_assignment_dept(db, ledger_payload, item, user_context)
    now = utc_now()
    seat.status = "assigned"
    seat.assignee_user_id = payload.assignee_user_id
    seat.assignee_name = payload.assignee_name or resolve_user_name(db, payload.assignee_user_id)
    seat.dept_id = dept_id
    seat.asset_id = payload.asset_id
    seat.assigned_at = now
    seat.returned_at = None
    seat.remark = payload.remark
    operator = operator_from_request(request)
    add_license_history(db, seat, "assign", operator, payload.remark)
    add_ledger(db, item, ledger_payload.model_copy(update={"assignee_name": seat.assignee_name, "dept_id": dept_id}), operator)
    sync_license_counts(db, item)
    db.commit()
    db.refresh(seat)
    return seat


@router.post("/license-seats/{seat_id}/return", response_model=LicenseSeatOut)
def return_license_seat(seat_id: int, payload: LicenseSeatReturn, request: Request, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    seat, item = require_license_seat(db, seat_id, user_context)
    writable_inventory_dept(item.dept_id, user_context)
    if seat.status != "assigned":
        raise HTTPException(status_code=400, detail="只有已分配席位可以回收")
    operator = operator_from_request(request)
    ledger_payload = InventoryLedgerCreate(action="return", quantity=1, assignee_user_id=seat.assignee_user_id, assignee_name=seat.assignee_name, dept_id=seat.dept_id, asset_id=seat.asset_id, remark=payload.remark)
    add_license_history(db, seat, "return", operator, payload.remark)
    add_ledger(db, item, ledger_payload, operator)
    seat.status = "recovered"
    seat.assignee_user_id = None
    seat.assignee_name = None
    seat.dept_id = None
    seat.asset_id = None
    seat.assigned_at = None
    seat.returned_at = utc_now()
    seat.remark = payload.remark
    sync_license_counts(db, item)
    db.commit()
    db.refresh(seat)
    return seat


@router.get("/license-seats/{seat_id}/history", response_model=list[LicenseSeatHistoryOut])
def license_seat_history(seat_id: int, request: Request, db: Session = Depends(get_db)):
    seat, _ = require_license_seat(db, seat_id, user_context_from_request(request))
    return db.query(InventoryLicenseSeatHistory).filter(InventoryLicenseSeatHistory.seat_id == seat.id).order_by(InventoryLicenseSeatHistory.created_at.desc(), InventoryLicenseSeatHistory.id.desc()).all()


@router.get("/items/{item_id}/installations", response_model=ComponentInstallationPage)
def component_installations(item_id: int, request: Request, keyword: str | None = None, page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    user_context = user_context_from_request(request)
    item = require_typed_item(db, item_id, "component", user_context)
    query = (
        db.query(InventoryComponentInstallation, Asset)
        .join(Asset, Asset.asset_id == InventoryComponentInstallation.asset_id)
        .filter(InventoryComponentInstallation.item_id == item.id)
    )
    query = AssetService.apply_data_scope(query, user_context)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(InventoryComponentInstallation.asset_id.like(pattern), Asset.name.like(pattern)))
    total = query.count()
    page = max(page, 1)
    page_size = min(max(page_size or 10, 1), 200)
    rows = query.order_by(InventoryComponentInstallation.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    result = [
        {
            "id": relation.id,
            "item_id": relation.item_id,
            "asset_id": relation.asset_id,
            "asset_name": asset.name or "",
            "quantity": relation.quantity,
            "dept_id": relation.dept_id,
            "installed_by": relation.installed_by,
            "installed_at": relation.installed_at,
            "remark": relation.remark,
            "updated_at": relation.updated_at,
        }
        for relation, asset in rows
    ]
    return {"list": result, "total": total, "page": page, "page_size": page_size}


def require_typed_item(db: Session, item_id: int, item_type: str, user_context: dict | None) -> InventoryItem:
    item = require_item(db, item_id, user_context)
    if item.item_type != item_type:
        raise HTTPException(status_code=400, detail="库存对象类型不匹配")
    return item


def require_license_seat(db: Session, seat_id: int, user_context: dict | None) -> tuple[InventoryLicenseSeat, InventoryItem]:
    query = (
        db.query(InventoryLicenseSeat, InventoryItem)
        .join(InventoryItem, InventoryItem.id == InventoryLicenseSeat.item_id)
        .filter(InventoryLicenseSeat.id == seat_id)
    )
    query = apply_inventory_scope(query, db, user_context)
    query = apply_license_seat_scope(query, user_context)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="授权席位不存在")
    return row


def apply_license_seat_scope(query, user_context: dict | None):
    if can_manage_all_inventory(user_context) or (is_department_manager(user_context) and scoped_dept_id(user_context)):
        return query
    identities = scoped_user_identities(user_context)
    if identities:
        return query.filter(InventoryLicenseSeat.assignee_user_id.in_(identities))
    return query.filter(False)


def add_license_seats(db: Session, item: InventoryItem, count: int, requested_codes: list[str], operator: str, remark: str | None = None) -> list[InventoryLicenseSeat]:
    clean_codes = list(dict.fromkeys(str(code).strip() for code in requested_codes if str(code or "").strip()))
    if len(clean_codes) != len([code for code in requested_codes if str(code or "").strip()]):
        raise HTTPException(status_code=409, detail="席位编号不能重复")
    existing_codes = {row[0] for row in db.query(InventoryLicenseSeat.seat_code).filter(InventoryLicenseSeat.item_id == item.id).all()}
    duplicated = existing_codes & set(clean_codes)
    if duplicated:
        raise HTTPException(status_code=409, detail=f"席位编号已存在：{sorted(duplicated)[0]}")
    target_count = max(int(count or 0), len(clean_codes))
    next_index = 1
    while len(clean_codes) < target_count:
        candidate = f"{item.code}-{next_index:03d}"
        next_index += 1
        if candidate not in existing_codes and candidate not in clean_codes:
            clean_codes.append(candidate)
    now = utc_now()
    seats = [InventoryLicenseSeat(item_id=item.id, seat_code=code, status="available", remark=remark, created_at=now, updated_at=now) for code in clean_codes]
    db.add_all(seats)
    db.flush()
    return seats


def reconcile_license_seats(db: Session, item: InventoryItem, target_total: int, operator: str, remark: str | None = None) -> None:
    if target_total < 0:
        raise HTTPException(status_code=400, detail="授权数量不能小于零")
    seats = db.query(InventoryLicenseSeat).filter(InventoryLicenseSeat.item_id == item.id).order_by(InventoryLicenseSeat.id.desc()).all()
    active = [seat for seat in seats if seat.status != "disabled"]
    delta = target_total - len(active)
    if delta > 0:
        disabled = [seat for seat in reversed(seats) if seat.status == "disabled"]
        for seat in disabled[:delta]:
            seat.status = "available"
            seat.remark = remark or "恢复授权席位"
            add_license_history(db, seat, "enable", operator, seat.remark)
        remaining = delta - min(len(disabled), delta)
        if remaining:
            add_license_seats(db, item, remaining, [], operator, remark)
    elif delta < 0:
        removable = [seat for seat in active if seat.status in {"available", "recovered"}]
        required = -delta
        if len(removable) < required:
            raise HTTPException(status_code=400, detail="已分配席位不能停用，请先回收授权")
        for seat in removable[:required]:
            seat.status = "disabled"
            seat.remark = remark or "减少授权数量"
            add_license_history(db, seat, "disable", operator, seat.remark)


def sync_license_counts(db: Session, item: InventoryItem) -> None:
    db.flush()
    seats = db.query(InventoryLicenseSeat.status).filter(InventoryLicenseSeat.item_id == item.id).all()
    statuses = [row[0] for row in seats]
    item.total_qty = sum(1 for status in statuses if status != "disabled")
    item.assigned_qty = statuses.count("assigned")
    item.available_qty = item.total_qty - item.assigned_qty


def add_license_history(db: Session, seat: InventoryLicenseSeat, action: str, operator: str, remark: str | None = None) -> None:
    db.add(
        InventoryLicenseSeatHistory(
            seat_id=seat.id,
            action=action,
            assignee_user_id=seat.assignee_user_id,
            assignee_name=seat.assignee_name,
            dept_id=seat.dept_id,
            asset_id=seat.asset_id,
            operator=operator,
            remark=remark,
        )
    )


def resolve_assignment_dept(db: Session, payload: InventoryLedgerCreate, item: InventoryItem, user_context: dict | None) -> str | None:
    requested = (payload.dept_id or "").strip()
    if not requested and payload.assignee_user_id:
        user = db.get(UserDirectory, payload.assignee_user_id)
        requested = (user.dept_id or user.dept_name or "") if user else ""
    if not requested and payload.asset_id:
        asset = db.get(Asset, payload.asset_id)
        requested = (asset.dept_id or "") if asset else ""
    return writable_inventory_dept(requested or item.dept_id, user_context)


def resolve_user_name(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    user = db.get(UserDirectory, user_id)
    return (user.display_name or user.username or user.user_id) if user else None


def update_component_installation(db: Session, item: InventoryItem, payload: InventoryLedgerCreate, quantity: int, operator: str, installing: bool) -> None:
    if not payload.asset_id:
        raise HTTPException(status_code=400, detail="组件装配或拆卸必须选择资产")
    relation = (
        db.query(InventoryComponentInstallation)
        .filter(InventoryComponentInstallation.item_id == item.id, InventoryComponentInstallation.asset_id == payload.asset_id)
        .first()
    )
    if installing:
        if not relation:
            asset = db.get(Asset, payload.asset_id)
            relation = InventoryComponentInstallation(
                item_id=item.id,
                asset_id=payload.asset_id,
                quantity=0,
                dept_id=payload.dept_id or (asset.dept_id if asset else None) or item.dept_id,
                installed_by=operator,
                installed_at=utc_now(),
            )
            db.add(relation)
        relation.quantity += quantity
        relation.installed_by = operator
        relation.remark = payload.remark
    else:
        if not relation or relation.quantity < quantity:
            raise HTTPException(status_code=400, detail="该资产上的组件安装数量不足")
        relation.quantity -= quantity
        relation.installed_by = operator
        relation.remark = payload.remark
        if relation.quantity == 0:
            db.delete(relation)


def require_item(db: Session, item_id: int, user_context: dict | None = None) -> InventoryItem:
    item = apply_inventory_scope(db.query(InventoryItem), db, user_context).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="库存对象不存在")
    return item


def apply_inventory_scope(query, db: Session, user_context: dict | None):
    if can_manage_all_inventory(user_context):
        return query
    dept_id = scoped_dept_id(user_context)
    if is_department_manager(user_context) and dept_id:
        return query.filter(InventoryItem.dept_id == dept_id)
    identities = scoped_user_identities(user_context)
    if identities:
        visible_item_ids = db.query(InventoryLedger.item_id).filter(InventoryLedger.assignee_user_id.in_(identities))
        return query.filter(InventoryItem.id.in_(visible_item_ids))
    return query.filter(False)


def apply_inventory_ledger_scope(query, user_context: dict | None):
    if can_manage_all_inventory(user_context):
        return query
    dept_id = scoped_dept_id(user_context)
    if is_department_manager(user_context) and dept_id:
        return query.filter(InventoryLedger.dept_id == dept_id)
    identities = scoped_user_identities(user_context)
    if identities:
        return query.filter(InventoryLedger.assignee_user_id.in_(identities))
    return query.filter(False)


def can_manage_all_inventory(user_context: dict | None) -> bool:
    role = ((user_context or {}).get("role") or "").lower()
    return can_view_all_data(user_context) or role == "asset_manager"


def writable_inventory_dept(requested_dept_id: str | None, user_context: dict | None) -> str | None:
    if can_manage_all_inventory(user_context):
        return (requested_dept_id or "").strip() or None
    dept_id = scoped_dept_id(user_context)
    if is_department_manager(user_context) and dept_id:
        return dept_id
    raise HTTPException(status_code=403, detail="当前账号不能维护部门库存")


def validate_inventory_targets(db: Session, payload: InventoryLedgerCreate, user_context: dict | None) -> None:
    if can_manage_all_inventory(user_context):
        return
    if payload.asset_id:
        asset = (
            AssetService.apply_data_scope(db.query(Asset), user_context)
            .filter(Asset.asset_id == payload.asset_id)
            .first()
        )
        if not asset:
            raise HTTPException(status_code=404, detail="关联资产不存在")
    if payload.assignee_user_id and is_department_manager(user_context):
        dept_id = scoped_dept_id(user_context)
        user = db.get(UserDirectory, payload.assignee_user_id)
        user_dept = (user.dept_id or user.dept_name) if user else None
        if not user or user_dept != dept_id:
            raise HTTPException(status_code=404, detail="领用人不存在")


def validate_type(item_type: str) -> None:
    if item_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="类型只能是 license、consumable、accessory、component")


def ensure_available(item: InventoryItem, quantity: int) -> None:
    if item.available_qty < quantity:
        raise HTTPException(status_code=400, detail="可用库存不足")


def add_ledger(db: Session, item: InventoryItem, payload: InventoryLedgerCreate, operator: str) -> None:
    db.add(InventoryLedger(item_id=item.id, operator=operator, **payload.model_dump()))


def build_summary(db: Session, user_context: dict | None = None, item_type: str | None = None, item_types: str | None = None) -> dict:
    from datetime import datetime, timedelta

    query = apply_inventory_scope(db.query(InventoryItem), db, user_context)
    if item_type:
        query = query.filter(InventoryItem.item_type == item_type)
    elif item_types:
        type_values = [value.strip() for value in item_types.split(",") if value.strip()]
        if type_values:
            query = query.filter(InventoryItem.item_type.in_(type_values))
    rows = query.all()
    expiring_deadline = utc_now() + timedelta(days=90)
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
