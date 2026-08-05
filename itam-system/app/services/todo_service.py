import re
import time
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.time import app_today, utc_now
from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.repair import RepairRecord
from app.models.user import UserDirectory
from app.services.asset_service import AssetService
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService
from app.services.scrap_service import ScrapService


class TodoService:
    INACTIVE_STATUSES = {"inactive", "disabled", "locked", "resigned", "left", "offboarded", "离职", "停用", "禁用"}
    SOURCE_LIMIT = 500
    BORROW_DUE_SOON_DAYS = 7
    CACHE_TTL_SECONDS = 45
    _cache: dict[str, tuple[float, list[dict]]] = {}

    @staticmethod
    def list_todos(db: Session, user_context: dict | None) -> list[dict]:
        key = TodoService.cache_key(user_context)
        now = time.monotonic()
        cached = TodoService._cache.get(key)
        if cached and now - cached[0] <= TodoService.CACHE_TTL_SECONDS:
            return cached[1]
        rows = TodoService.build_todos(db, user_context or {})
        TodoService._cache[key] = (now, rows)
        TodoService.prune_cache(now)
        return rows

    @staticmethod
    def invalidate() -> None:
        TodoService._cache.clear()

    @staticmethod
    def cache_key(user_context: dict | None) -> str:
        user_context = user_context or {}
        return "|".join([
            str(user_context.get("role") or ""),
            str(user_context.get("user_id") or ""),
            str(user_context.get("username") or ""),
            str(user_context.get("dept_id") or user_context.get("dept_name") or ""),
        ])

    @staticmethod
    def prune_cache(now: float) -> None:
        expired = [key for key, (created_at, _) in TodoService._cache.items() if now - created_at > TodoService.CACHE_TTL_SECONDS * 3]
        for key in expired:
            TodoService._cache.pop(key, None)

    @staticmethod
    def build_todos(db: Session, user_context: dict) -> list[dict]:
        purchase_result = PurchaseService.list_purchases(db, page=1, page_size=TodoService.SOURCE_LIMIT, user_context=user_context)
        scrap_result = ScrapService.list_requests(db, page=1, page_size=TodoService.SOURCE_LIMIT, status="待处置", user_context=user_context)
        repair_result = RepairService.list_records(db, page=1, page_size=TodoService.SOURCE_LIMIT, status="维修中", user_context=user_context)
        asset_query = AssetService.apply_data_scope(db.query(Asset), user_context)

        purchases = purchase_result["list"]
        scraps = scrap_result["list"]
        repairs = repair_result["list"]
        assets = asset_query.order_by(Asset.created_at.desc()).limit(TodoService.SOURCE_LIMIT).all()
        users = TodoService.scoped_users(db, user_context)
        inactive_user_map = TodoService.inactive_user_map(users)
        assigned_user_ids = TodoService.assigned_user_ids_from_db(db, user_context)

        rows = [
            *TodoService.onboarding_todos(users, assigned_user_ids),
            *TodoService.purchase_todos(purchases),
            *TodoService.scrap_todos(scraps),
            *TodoService.ready_scrap_todos(assets),
            *TodoService.offboarding_todos(assets, inactive_user_map),
            *TodoService.borrow_due_todos(assets),
            *TodoService.repair_todos(repairs),
        ]
        return sorted(rows, key=lambda item: (-TodoService.priority_weight(item.get("priority")), -TodoService.date_value(item.get("created_at"))))

    @staticmethod
    def scoped_users(db: Session, user_context: dict):
        query = db.query(UserDirectory)
        if can_view_all_data(user_context):
            return query.all()
        dept_id = scoped_dept_id(user_context)
        identities = scoped_user_identities(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter((UserDirectory.dept_id == dept_id) | (UserDirectory.dept_name == dept_id)).all()
        if identities:
            return query.filter((UserDirectory.user_id.in_(identities)) | (UserDirectory.username.in_(identities))).all()
        return []

    @staticmethod
    def onboarding_todos(users: list[UserDirectory], assigned_user_ids: set[str]) -> list[dict]:
        rows = []
        for user in users:
            if str(user.status or "").lower() != "active" or user.role in {"admin", "auditor"}:
                continue
            if user.asset_assignment_required is False:
                continue
            if TodoService.user_has_assigned_asset(user, assigned_user_ids):
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

    @staticmethod
    def purchase_todos(purchases) -> list[dict]:
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

    @staticmethod
    def scrap_todos(scraps) -> list[dict]:
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

    @staticmethod
    def ready_scrap_todos(assets: list[Asset]) -> list[dict]:
        return [{
            "id": f"ready-scrap-{item.asset_id}",
            "type": "scrap_request",
            "type_label": "报废处置",
            "title": f"{item.asset_id} 待提交报废处置登记",
            "description": f"{item.name or '资产'} / {item.category or '-'} / 当前状态：{TodoService.status_label(item.status)}",
            "owner": item.owner_user_id or "资产管理员",
            "priority": "medium",
            "status": "待提交",
            "created_at": item.created_at,
            "asset_id": item.asset_id,
            "target_path": "/asset/list",
            "target_query": {"status": "ready_scrap", "keyword": item.asset_id},
        } for item in assets if item.status == "ready_scrap"]

    @staticmethod
    def offboarding_todos(assets: list[Asset], inactive_user_map: dict[str, UserDirectory]) -> list[dict]:
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
                "created_at": TodoService.latest_date(user_assets),
                "asset_count": len(user_assets),
                "asset_ids": [asset.asset_id for asset in user_assets],
                "user_id": user.user_id,
                "username": user.username or "",
                "name": name,
                "target_path": "/asset/list",
                "target_query": {"action": "reclaim", "user_id": user.user_id, "username": user.username or "", "name": name},
            })
        return rows

    @staticmethod
    def borrow_due_todos(assets: list[Asset]) -> list[dict]:
        today = app_today()
        soon_deadline = today + timedelta(days=TodoService.BORROW_DUE_SOON_DAYS)
        rows = []
        for asset in assets:
            if asset.status != "borrowed":
                continue
            due_date = TodoService.parse_date((asset.config or {}).get("borrow_due_date"))
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

    @staticmethod
    def repair_todos(repairs: list[dict | RepairRecord]) -> list[dict]:
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

    @staticmethod
    def inactive_user_map(users: list[UserDirectory]) -> dict[str, UserDirectory]:
        mapping = {}
        for user in users:
            if str(user.status or "").lower() not in TodoService.INACTIVE_STATUSES:
                continue
            for value in [user.user_id, user.username]:
                if value:
                    mapping[value] = user
        return mapping

    @staticmethod
    def assigned_user_ids(assets: list[Asset]) -> set[str]:
        ids = set()
        for asset in assets:
            if asset.status not in {"in_use", "borrowed", "out_stock"}:
                continue
            if asset.owner_user_id:
                ids.update(TodoService.identity_keys(asset.owner_user_id))
        return ids

    @staticmethod
    def assigned_user_ids_from_db(db: Session, user_context: dict) -> set[str]:
        query = AssetService.apply_data_scope(db.query(Asset.owner_user_id), user_context)
        rows = (
            query
            .filter(Asset.status.in_(["in_use", "borrowed", "out_stock"]))
            .filter(Asset.owner_user_id.isnot(None), Asset.owner_user_id != "")
            .distinct()
            .all()
        )
        ids: set[str] = set()
        for row in rows:
            ids.update(TodoService.identity_keys(row[0]))
        return ids

    @staticmethod
    def user_has_assigned_asset(user: UserDirectory, assigned_user_ids: set[str]) -> bool:
        return any(key in assigned_user_ids for value in [
            user.user_id,
            user.username,
            user.external_id,
            user.email,
            user.display_name,
        ] for key in TodoService.identity_keys(value))

    @staticmethod
    def identity_key(value: str | None) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def identity_keys(value: str | None) -> set[str]:
        raw = TodoService.identity_key(value)
        if not raw:
            return set()
        ldap_cn = re.search(r"(?:^|[:,/])cn=([^,/:]+)", raw)
        if ldap_cn:
            # LDAP DN 中的 ou/dc 等片段由所有目录用户共享，不能作为人员别名。
            return {raw, ldap_cn.group(1).strip().casefold()}
        parts = {
            item.strip().casefold()
            for item in re.split(r"[\s\-_/\\|,;:，；：()（）]+", raw)
            if item.strip()
        }
        parts.add(raw)
        return parts

    @staticmethod
    def priority_weight(priority: str | None) -> int:
        return {"high": 3, "medium": 2, "low": 1}.get(priority or "", 0)

    @staticmethod
    def date_value(value) -> float:
        if isinstance(value, datetime):
            return value.timestamp()
        if not value:
            return 0
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0

    @staticmethod
    def latest_date(items: list[Asset]):
        return max((item.created_at for item in items if item.created_at), default=None)

    @staticmethod
    def parse_date(value) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    @staticmethod
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
