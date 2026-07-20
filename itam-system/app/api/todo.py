from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities, user_context_from_request
from app.models.asset import Asset
from app.models.purchase import Purchase
from app.models.repair import RepairRecord
from app.models.scrap import ScrapRequest
from app.models.user import UserDirectory
from app.services.asset_service import AssetService
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService
from app.services.scrap_service import ScrapService
from app.services.todo_service import TodoService


router = APIRouter(prefix="/todo", tags=["Todo"])

INACTIVE_STATUSES = {"inactive", "disabled", "locked", "resigned", "left", "offboarded", "离职", "停用", "禁用"}
TODO_SOURCE_LIMIT = 500
BORROW_DUE_SOON_DAYS = 7


@router.get("/list")
def list_todos(request: Request, db: Session = Depends(get_db)):
    return TodoService.list_todos(db, user_context_from_request(request))


def build_onboarding_todos(users: list[UserDirectory], assigned_user_ids: set[str]) -> list[dict]:
    rows = []
    for user in users:
        if str(user.status or "").lower() != "active":
            continue
        if user.role in {"admin", "auditor"}:
            continue
        if user.user_id in assigned_user_ids or user.username in assigned_user_ids:
            continue
        name = user.display_name or user.username or user.user_id
        rows.append({
            "id": f"onboarding-{user.user_id or user.username}",
            "type": "onboarding_assign",
            "type_label": "入职配置",
            "title": f"{name} 待配置入职资产",
            "description": f"{user.dept_name or user.dept_id or '未设置部门'} / {user.email or '未填写邮箱'} / 当前未绑定资产",
            "owner": name,
            "priority": "medium",
            "status": "待分配",
            "created_at": user.created_at,
            "user_id": user.user_id,
            "username": user.username or "",
            "name": name,
            "target_path": "/asset/list",
            "target_query": {"action": "assign", "user_id": user.user_id, "username": user.username or "", "name": name},
        })
    return rows


def build_purchase_todos(purchases: list[Purchase]) -> list[dict]:
    rows = []
    for item in purchases:
        if item.status != "pending_acceptance":
            continue
        quantity = sum(int(row.quantity or 0) for row in item.items)
        rows.append({
            "id": f"purchase-accept-{item.purchase_no}",
            "type": "purchase_acceptance",
            "type_label": "采购验收",
            "title": f"采购单 {item.purchase_no} 待验收",
            "description": f"{item.company or '未指定公司'} / {item.supplier_name or '未指定供应商'} / {quantity} 台需要验收入库",
            "owner": "采购验收员",
            "priority": "medium",
            "status": "待验收",
            "created_at": item.created_at,
            "purchase_no": item.purchase_no,
            "target_path": "/purchase",
            "target_query": {"todo": "purchase_acceptance", "purchase_no": item.purchase_no},
        })
    return rows


def build_scrap_todos(scraps: list[ScrapRequest]) -> list[dict]:
    return [{
        "id": f"scrap-disposal-{item.id or item.request_no}",
        "type": "scrap_disposal",
        "type_label": "报废处置",
        "title": f"{item.asset_id} 待登记报废处置",
        "description": f"{item.asset_name or '资产'} / {item.reason or '未填写原因'} / 预计残值 ¥{item.estimated_residual_value or 0:,.0f}",
        "owner": "资产负责人",
        "priority": "high",
        "status": item.status or "待处置",
        "created_at": item.created_at,
        "request_id": item.id,
        "request_no": item.request_no,
        "asset_id": item.asset_id,
        "target_path": "/scrap",
        "target_query": {"todo": "scrap_disposal", "request_no": item.request_no},
    } for item in scraps]


def build_ready_scrap_todos(assets: list[Asset]) -> list[dict]:
    return [{
        "id": f"ready-scrap-{item.asset_id}",
        "type": "scrap_request",
        "type_label": "报废处置",
        "title": f"{item.asset_id} 待提交报废处置登记",
        "description": f"{item.name or '资产'} / {item.category or '-'} / 当前状态：{status_label(item.status)}",
        "owner": item.owner_user_id or "资产管理员",
        "priority": "medium",
        "status": "待提交",
        "created_at": item.created_at,
        "asset_id": item.asset_id,
        "target_path": "/asset/list",
        "target_query": {"status": "ready_scrap", "keyword": item.asset_id},
    } for item in assets if item.status == "ready_scrap"]


def build_offboarding_todos(assets: list[Asset], inactive_user_map: dict[str, UserDirectory]) -> list[dict]:
    groups: dict[str, dict] = {}
    for asset in assets:
        if asset.status not in {"in_use", "borrowed", "out_stock", "repair"}:
            continue
        user = inactive_user_map.get(asset.owner_user_id or "")
        if not user:
            continue
        key = user.user_id or user.username or asset.owner_user_id
        groups.setdefault(key, {"user": user, "assets": []})["assets"].append(asset)
    rows = []
    for group in groups.values():
        user = group["user"]
        user_assets = group["assets"]
        first = user_assets[0]
        name = user.display_name or user.username or user.user_id
        preview = "、".join(asset.asset_id for asset in user_assets[:3])
        more = f" 等 {len(user_assets)} 个资产" if len(user_assets) > 3 else f" {len(user_assets)} 个资产"
        rows.append({
            "id": f"offboarding-{user.user_id or user.username}",
            "type": "offboarding_reclaim",
            "type_label": "离职回收",
            "title": f"{name} 的离职资产待批量回收",
            "description": f"{preview}{more} / {first.location or '未填写位置'}",
            "owner": name,
            "priority": "high",
            "status": "待回收",
            "created_at": latest_date(user_assets),
            "asset_count": len(user_assets),
            "asset_ids": [asset.asset_id for asset in user_assets],
            "user_id": user.user_id,
            "username": user.username or "",
            "name": name,
            "target_path": "/asset/list",
            "target_query": {"action": "reclaim", "user_id": user.user_id, "username": user.username or "", "name": name},
        })
    return rows


def build_borrow_due_todos(assets: list[Asset]) -> list[dict]:
    today = datetime.utcnow().date()
    soon_deadline = today + timedelta(days=BORROW_DUE_SOON_DAYS)
    rows = []
    for asset in assets:
        if asset.status != "borrowed":
            continue
        due_date = parse_date((asset.config or {}).get("borrow_due_date"))
        if not due_date or due_date > soon_deadline:
            continue
        overdue = due_date < today
        rows.append({
            "id": f"borrow-due-{asset.asset_id}",
            "type": "borrow_due_return",
            "type_label": "借用归还",
            "title": f"{asset.asset_id} 借用{'已超期' if overdue else '即将到期'}",
            "description": f"{asset.name} / 借用人：{asset.owner_user_id or '-'} / 到期：{due_date.isoformat()} / {asset.location or '未填写位置'}",
            "owner": asset.owner_user_id or "资产管理员",
            "priority": "high" if overdue else "medium",
            "status": "已超期" if overdue else "即将到期",
            "created_at": due_date.isoformat(),
            "asset_id": asset.asset_id,
            "borrow_due_date": due_date.isoformat(),
            "target_path": "/asset/list",
            "target_query": {"status": "borrowed", "keyword": asset.asset_id},
        })
    return rows


def build_repair_todos(repairs: list[dict | RepairRecord]) -> list[dict]:
    def value(item, field):
        return item.get(field) if isinstance(item, dict) else getattr(item, field, None)

    return [{
        "id": f"repair-{value(item, 'id') or value(item, 'repair_no')}",
        "type": "repair_followup",
        "type_label": "维修跟进",
        "title": f"{value(item, 'asset_id')} 维修中待跟进",
        "description": f"{value(item, 'fault_reason') or '未填写故障原因'} / {value(item, 'vendor') or '未填写维修商'}",
        "owner": value(item, "operator") or "资产管理员",
        "priority": "low",
        "status": "维修中",
        "created_at": value(item, "repair_time") or value(item, "created_at"),
        "repair_id": value(item, "id"),
        "repair_no": value(item, "repair_no"),
        "asset_id": value(item, "asset_id"),
        "target_path": "/repair",
        "target_query": {"todo": "repair_followup", "repair_no": value(item, "repair_no")},
    } for item in repairs if value(item, "status") == "维修中"]


def build_inactive_user_map(users: list[UserDirectory]) -> dict[str, UserDirectory]:
    mapping = {}
    for user in users:
        if str(user.status or "").lower() not in INACTIVE_STATUSES:
            continue
        for value in [user.user_id, user.username]:
            if value:
                mapping[value] = user
    return mapping


def build_assigned_user_ids(assets: list[Asset]) -> set[str]:
    ids = set()
    for asset in assets:
        if asset.status not in {"in_use", "borrowed", "out_stock"}:
            continue
        if asset.owner_user_id:
            ids.add(asset.owner_user_id)
    return ids


def priority_weight(priority: str | None) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(priority or "", 0)


def date_value(value) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if not value:
        return 0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def latest_date(items: list[Asset]):
    return max((item.created_at for item in items if item.created_at), default=None)


def parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def status_label(status: str | None) -> str:
    return {
        "in_stock": "在库",
        "in_use": "在用",
        "idle": "闲置",
        "borrowed": "借出",
        "repair": "维修中",
        "out_stock": "已出库",
        "ready_scrap": "待报废",
    }.get(status or "", status or "-")
