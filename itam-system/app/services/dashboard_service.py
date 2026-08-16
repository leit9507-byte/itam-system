from collections import Counter
import copy
import time
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, defer, joinedload

from app.core.time import app_day_bounds, app_datetime_to_utc, utc_now
from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.lifecycle import Lifecycle
from app.models.product import ProductCatalog
from app.models.purchase import Purchase, PurchaseItem
from app.models.repair import RepairRecord
from app.models.scrap import ScrapRequest
from app.models.user import UserDirectory
from app.services.asset_service import AssetService
from app.services.asset_residual_service import AssetResidualService


class DashboardService:
    CATEGORY_NAMES = ["笔记本电脑", "台式机", "Mac设备", "显示器", "服务器", "存储设备", "网络设备", "软件授权", "其他"]
    LIFECYCLE_NAMES = {
        "pending_acceptance": "待验收",
        "in_stock": "库存中",
        "in_use": "已领用",
        "repair": "维修中",
        "idle": "闲置",
        "ready_scrap": "待报废",
        "pending_scrap": "待处置登记",
        "scrapped": "已报废",
        "disposed": "已处置",
        "lost": "已丢失",
    }
    INACTIVE_USER_STATUSES = {"inactive", "disabled", "locked", "resigned", "left", "offboarded", "离职", "停用", "禁用"}

    CACHE_TTL_SECONDS = 45
    _cache: dict[str, tuple[float, dict]] = {}

    @staticmethod
    def invalidate() -> None:
        DashboardService._cache.clear()

    @staticmethod
    def enterprise(db: Session, user_context: dict | None = None, date_range: list[str] | None = None) -> dict:
        cache_key = DashboardService.cache_key(user_context, date_range)
        now_monotonic = time.monotonic()
        cached = DashboardService._cache.get(cache_key)
        if cached and now_monotonic - cached[0] <= DashboardService.CACHE_TTL_SECONDS:
            return copy.deepcopy(cached[1])

        now = utc_now()
        summary = AssetService.asset_summary(db, user_context)
        managed_query = AssetService.apply_data_scope(db.query(Asset), user_context).filter(or_(Asset.status.is_(None), ~Asset.status.in_(["scrapped", "disposed", "lost"])))
        # 只加载仪表盘计算所需的列：跳过 remark/sn/审批单号/供应商等大字段，降低内存与网络开销
        assets_for_detail = managed_query.options(
            defer(Asset.remark),
            defer(Asset.sn),
            defer(Asset.company),
            defer(Asset.purchase_approval_no),
            defer(Asset.purchase_supplier_name),
        ).all()
        products = db.query(ProductCatalog).all()
        product_index = DashboardService.product_retirement_index(products)
        products = product_index

        scoped_assets = DashboardService.filter_by_date_range(assets_for_detail, date_range, "created_at")
        assets = scoped_assets if date_range else assets_for_detail
        use_global_summary = not date_range
        status_counts = summary["managed_status_counts"] if use_global_summary else Counter(asset.status or "unknown" for asset in assets)
        category_counts = summary["managed_category_counts"] if use_global_summary else Counter(asset.category or "其他" for asset in assets)

        total = int(summary["managed_total"] if use_global_summary else len(assets))
        original_value = float(summary["managed_total_value"] if use_global_summary else sum(float(asset.purchase_price or 0) for asset in assets))
        residual_config = AssetResidualService.get_config(db)
        net_value = round(
            sum(
                AssetResidualService.calculate_asset(
                    asset,
                    as_of=now,
                    residual_config=residual_config,
                )
                for asset in assets
            ),
            2,
        )
        this_month = DashboardService.month_start(now, 0)
        previous_month = DashboardService.month_start(now, 1)
        current_month_count = int(summary["current_month_managed_count"] if use_global_summary else sum(1 for asset in assets if asset.created_at and asset.created_at >= this_month))
        previous_month_count = int(summary["previous_month_managed_count"] if use_global_summary else sum(1 for asset in assets if asset.created_at and previous_month <= asset.created_at < this_month))

        purchases = DashboardService.scoped_purchases(db, user_context, date_range)
        scraps = DashboardService.scoped_scraps(db, user_context, date_range)
        retirement_assets = DashboardService.retirement_soon_assets(assets, product_index, now)
        repair_dashboard = DashboardService.repair_dashboard(db, user_context)
        lifecycles = DashboardService.scoped_lifecycles(db, user_context, limit=20)
        users = DashboardService.scoped_users(db, user_context)

        result = {
            "metrics": [
                DashboardService.metric("在管资产", total, "项", "", DashboardService.compare(total, max(total - current_month_count, 0)), DashboardService.asset_month_trend(assets_for_detail, "count", now), "primary"),
                DashboardService.metric("资产原值", original_value, "", "¥", DashboardService.compare(DashboardService.sum_assets_by_month(assets_for_detail, 0, now), DashboardService.sum_assets_by_month(assets_for_detail, 1, now)), DashboardService.asset_month_trend(assets, "value", now), "success"),
                DashboardService.metric(
                    "资产净值",
                    net_value,
                    "",
                    "¥",
                    "按残值规则",
                    DashboardService.asset_month_trend(assets, "net", now, residual_config),
                    "warning",
                ),
                DashboardService.metric("在用资产", int(status_counts.get("in_use", 0)), "项", "", "实时", DashboardService.status_trend(status_counts, "in_use"), "success"),
                DashboardService.metric("闲置资产", int(status_counts.get("idle", 0)), "项", "", "实时", DashboardService.status_trend(status_counts, "idle"), "warning"),
                DashboardService.metric("维修中资产", int(status_counts.get("repair", 0)), "项", "", "实时", DashboardService.status_trend(status_counts, "repair"), "danger"),
                DashboardService.metric("本月新增资产", current_month_count, "项", "", DashboardService.compare(current_month_count, previous_month_count), DashboardService.asset_month_trend(assets_for_detail, "count", now), "primary"),
                DashboardService.metric("即将过保资产", len(retirement_assets), "项", "", "180天内", DashboardService.retirement_month_trend(assets, products, now), "danger"),
            ],
            "categoryDistribution": DashboardService.category_distribution(category_counts),
            "departmentDistribution": DashboardService.department_distribution(assets),
            "purchaseTrend": DashboardService.purchase_trend(purchases, now),
            "scrapTrend": DashboardService.scrap_trend(scraps, now),
            "retirementTrend": DashboardService.retirement_due_trend(assets_for_detail, products, now),
            "lifecycleDistribution": DashboardService.lifecycle_distribution(status_counts, purchases),
            "retirementSoonAssets": retirement_assets,
            "maintenance": DashboardService.maintenance(repair_dashboard, assets),
            "statusCounts": {
                "in_use": int(status_counts.get("in_use", 0)),
                "idle": int(status_counts.get("idle", 0)),
                "repair": int(status_counts.get("repair", 0)),
                "scrapped": int(summary["status_counts"].get("scrapped", 0) if use_global_summary else sum(1 for asset in assets if asset.status == "scrapped")),
                "lost": int(summary["status_counts"].get("lost", 0) if use_global_summary else sum(1 for asset in assets if asset.status == "lost")),
                "pending_scrap": int(status_counts.get("ready_scrap", 0)) + int(status_counts.get("pending_scrap", 0)),
            },
            "personnelTrend": DashboardService.personnel_trend(users, now),
            "recentRecords": DashboardService.recent_records(lifecycles, assets),
            "warrantyRows": DashboardService.warranty_rows(retirement_assets),
        }
        DashboardService._cache[cache_key] = (now_monotonic, copy.deepcopy(result))
        DashboardService.prune_cache(now_monotonic)
        return result

    @staticmethod
    def cache_key(user_context: dict | None, date_range: list[str] | None) -> str:
        user_context = user_context or {}
        return "|".join([
            str(user_context.get("role") or ""),
            str(user_context.get("user_id") or ""),
            str(user_context.get("username") or ""),
            str(user_context.get("dept_id") or user_context.get("dept_name") or ""),
            ",".join(date_range or []),
        ])

    @staticmethod
    def prune_cache(now: float) -> None:
        expired = [
            key
            for key, (created_at, _) in DashboardService._cache.items()
            if now - created_at > DashboardService.CACHE_TTL_SECONDS * 3
        ]
        for key in expired:
            DashboardService._cache.pop(key, None)

    @staticmethod
    def metric(label, value, suffix, prefix, change, trend, tone) -> dict:
        return {"label": label, "value": value, "suffix": suffix, "prefix": prefix, "change": change, "trend": trend, "tone": tone}

    @staticmethod
    def scoped_purchases(db: Session, user_context: dict | None, date_range: list[str] | None):
        query = db.query(Purchase).options(joinedload(Purchase.items))
        if not can_view_all_data(user_context):
            dept_id = scoped_dept_id(user_context)
            identities = scoped_user_identities(user_context)
            if is_department_manager(user_context) and dept_id:
                query = query.join(Purchase.items).filter((PurchaseItem.dept_id == dept_id)).distinct()
            elif identities:
                query = query.filter(False)
            else:
                query = query.filter(False)
        query = DashboardService.apply_date_filter(query, Purchase.created_at, date_range)
        return query.order_by(Purchase.created_at.desc()).all()

    @staticmethod
    def scoped_scraps(db: Session, user_context: dict | None, date_range: list[str] | None):
        query = db.query(ScrapRequest)
        query = DashboardService.apply_asset_like_scope(query, ScrapRequest, user_context)
        query = DashboardService.apply_date_filter(query, ScrapRequest.created_at, date_range)
        return query.order_by(ScrapRequest.created_at.desc()).all()

    @staticmethod
    def scoped_lifecycles(db: Session, user_context: dict | None, limit: int):
        query = db.query(Lifecycle).join(Asset, Asset.asset_id == Lifecycle.asset_id)
        query = AssetService.apply_data_scope(query, user_context)
        return query.order_by(Lifecycle.timestamp.desc()).limit(limit).all()

    @staticmethod
    def scoped_users(db: Session, user_context: dict | None):
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
    def apply_asset_like_scope(query, model, user_context: dict | None):
        if can_view_all_data(user_context):
            return query
        dept_id = scoped_dept_id(user_context)
        identities = scoped_user_identities(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter(model.dept_id == dept_id)
        if identities:
            return query.filter(model.owner_user_id.in_(identities))
        return query.filter(False)

    @staticmethod
    def apply_date_filter(query, column, date_range: list[str] | None):
        start, end = DashboardService.parse_date_range(date_range)
        if start:
            query = query.filter(column >= start)
        if end:
            query = query.filter(column <= end)
        return query

    @staticmethod
    def parse_date_range(date_range: list[str] | None):
        if not date_range or len(date_range) < 2:
            return None, None
        try:
            start_date = datetime.fromisoformat(date_range[0]).date()
            end_date = datetime.fromisoformat(date_range[1]).date()
            start, _ = app_day_bounds(start_date)
            _, end = app_day_bounds(end_date)
            return start, end
        except ValueError:
            return None, None

    @staticmethod
    def filter_by_date_range(rows, date_range, key):
        start, end = DashboardService.parse_date_range(date_range)
        if not start or not end:
            return rows
        return [
            row
            for row in rows
            if getattr(row, key, None)
            and start <= app_datetime_to_utc(getattr(row, key)) <= end
        ]

    @staticmethod
    def compare(current, previous) -> str:
        current = float(current or 0)
        previous = float(previous or 0)
        if not previous and not current:
            return "无变化"
        if not previous:
            return "新增" if current else "无变化"
        rate = round(((current - previous) / previous) * 100)
        return f"{'+' if rate >= 0 else ''}{rate}%"

    @staticmethod
    def month_start(now: datetime, offset: int) -> datetime:
        month_index = now.year * 12 + now.month - 1 - offset
        year = month_index // 12
        month = month_index % 12 + 1
        return datetime(year, month, 1)

    @staticmethod
    def last_months(size: int, now: datetime):
        return [DashboardService.month_start(now, size - 1 - index) for index in range(size)]

    @staticmethod
    def next_months(size: int, now: datetime):
        return [DashboardService.add_months(datetime(now.year, now.month, 1), index) for index in range(size)]

    @staticmethod
    def add_months(value: datetime, months: int) -> datetime:
        month_index = value.year * 12 + value.month - 1 + months
        year = month_index // 12
        month = month_index % 12 + 1
        return datetime(year, month, 1)

    @staticmethod
    def month_label(value: datetime) -> str:
        return f"{value.month}月"

    @staticmethod
    def in_month(value: datetime | None, month: datetime) -> bool:
        return bool(value and value.year == month.year and value.month == month.month)

    @staticmethod
    def asset_month_trend(
        assets: list[Asset],
        mode: str,
        now: datetime,
        residual_config: dict | None = None,
    ) -> list[float]:
        rows = []
        for month in DashboardService.last_months(5, now):
            month_assets = [asset for asset in assets if DashboardService.in_month(asset.created_at, month)]
            if mode == "value":
                rows.append(sum(float(asset.purchase_price or 0) for asset in month_assets))
            elif mode == "net":
                rows.append(
                    round(
                        sum(
                            AssetResidualService.calculate_asset(
                                asset,
                                as_of=now,
                                residual_config=residual_config,
                            )
                            for asset in month_assets
                        ),
                        2,
                    )
                )
            else:
                rows.append(len(month_assets))
        return rows

    @staticmethod
    def sum_assets_by_month(assets: list[Asset], offset: int, now: datetime) -> float:
        month = DashboardService.month_start(now, offset)
        return sum(float(asset.purchase_price or 0) for asset in assets if DashboardService.in_month(asset.created_at, month))

    @staticmethod
    def status_trend(status_counts, status: str) -> list[int]:
        return [0, 0, 0, 0, int(status_counts.get(status, 0))]

    @staticmethod
    def category_distribution(counts) -> list[dict]:
        normalized = {name: 0 for name in DashboardService.CATEGORY_NAMES}
        for category, value in dict(counts).items():
            normalized[DashboardService.normalize_category(category)] += int(value or 0)
        return [{"name": name, "value": value} for name, value in normalized.items()]

    @staticmethod
    def normalize_category(category: str | None) -> str:
        raw = str(category or "").lower()
        if "laptop" in raw or "notebook" in raw or "笔记本" in raw:
            return "笔记本电脑"
        if "desktop" in raw or "台式" in raw:
            return "台式机"
        if "mac" in raw:
            return "Mac设备"
        if "monitor" in raw or "display" in raw or "显示" in raw:
            return "显示器"
        if "server" in raw or "服务器" in raw:
            return "服务器"
        if "storage" in raw or "存储" in raw:
            return "存储设备"
        if "network" in raw or "交换" in raw or "网络" in raw:
            return "网络设备"
        if "software" in raw or "license" in raw or "授权" in raw:
            return "软件授权"
        return category if category in DashboardService.CATEGORY_NAMES else "其他"

    @staticmethod
    def department_distribution(assets: list[Asset]) -> list[dict]:
        rows = Counter(DashboardService.normalize_department(asset.dept_id or asset.location) for asset in assets)
        return [{"name": name, "value": value} for name, value in sorted(rows.items(), key=lambda item: (-item[1], item[0]))]

    @staticmethod
    def normalize_department(value: str | None) -> str:
        raw = str(value or "").strip()
        return raw or "未绑定"

    @staticmethod
    def purchase_trend(purchases: list[Purchase], now: datetime) -> dict:
        months = DashboardService.last_months(12, now)
        return {
            "months": [DashboardService.month_label(month) for month in months],
            "amount": [sum(float(row.total_amount or 0) for row in purchases if DashboardService.in_month(row.created_at, month)) for month in months],
            "quantity": [
                sum(sum(int(item.quantity or 0) for item in row.items) for row in purchases if DashboardService.in_month(row.created_at, month))
                for month in months
            ],
        }

    @staticmethod
    def scrap_trend(scraps: list[ScrapRequest], now: datetime) -> dict:
        months = DashboardService.last_months(12, now)
        return {
            "months": [DashboardService.month_label(month) for month in months],
            "submitted": [sum(1 for row in scraps if DashboardService.in_month(row.created_at, month)) for month in months],
            "approved": [sum(1 for row in scraps if row.status == "已通过" and DashboardService.in_month(row.approved_at or row.created_at, month)) for month in months],
        }

    @staticmethod
    def lifecycle_distribution(status_counts, purchases: list[Purchase]) -> list[dict]:
        count = lambda status: int(status_counts.get(status, 0))
        return [
            {"name": DashboardService.LIFECYCLE_NAMES["pending_acceptance"], "value": count("pending_acceptance") + sum(1 for item in purchases if item.status == "pending_acceptance")},
            {"name": DashboardService.LIFECYCLE_NAMES["in_stock"], "value": count("in_stock")},
            {"name": DashboardService.LIFECYCLE_NAMES["in_use"], "value": count("in_use")},
            {"name": DashboardService.LIFECYCLE_NAMES["repair"], "value": count("repair")},
            {"name": DashboardService.LIFECYCLE_NAMES["idle"], "value": count("idle")},
            {"name": DashboardService.LIFECYCLE_NAMES["ready_scrap"], "value": count("ready_scrap")},
            {"name": DashboardService.LIFECYCLE_NAMES["pending_scrap"], "value": count("pending_scrap")},
            {"name": DashboardService.LIFECYCLE_NAMES["scrapped"], "value": count("scrapped")},
            {"name": DashboardService.LIFECYCLE_NAMES["disposed"], "value": count("disposed")},
            {"name": DashboardService.LIFECYCLE_NAMES["lost"], "value": count("lost")},
        ]

    @staticmethod
    def retirement_soon_assets(assets: list[Asset], products: list[ProductCatalog], now: datetime) -> list[dict]:
        deadline_days = 180
        rows = []
        for asset in assets:
            date = DashboardService.resolve_warranty_or_retirement_date(asset, products)
            if not date:
                continue
            days = (date.date() - now.date()).days
            if days > deadline_days:
                continue
            rows.append({
                "asset_id": asset.asset_id,
                "name": asset.name,
                "brand": asset.brand,
                "model": asset.model,
                "retirement_date": date.date().isoformat(),
                "days_remaining": days,
                "overdue": days < 0,
            })
        return sorted(rows, key=lambda item: item["days_remaining"])[:200]

    @staticmethod
    def resolve_warranty_or_retirement_date(asset: Asset, products: list[ProductCatalog]) -> datetime | None:
        if asset.warranty_expire_date:
            return asset.warranty_expire_date
        years = DashboardService.resolve_retirement_years(asset, products)
        if not years or not asset.purchase_date:
            return None
        try:
            return asset.purchase_date.replace(year=asset.purchase_date.year + years)
        except ValueError:
            return asset.purchase_date.replace(month=2, day=28, year=asset.purchase_date.year + years)

    @staticmethod
    def resolve_retirement_years(asset: Asset, products: list[ProductCatalog] | dict[str, int]) -> int:
        config = asset.config or {}
        if config.get("retirement_years"):
            return int(config["retirement_years"])
        if isinstance(products, dict):
            for key in DashboardService.product_lookup_keys(asset):
                if key in products:
                    return int(products[key] or 0)
            return 0
        for product in products:
            if DashboardService.product_matches_asset(product, asset):
                return int(product.retirement_years or 0)
        return 0

    @staticmethod
    def product_retirement_index(products: list[ProductCatalog]) -> dict[str, int]:
        rows: dict[str, int] = {}
        for product in products:
            years = int(product.retirement_years or 0)
            if not years:
                continue
            name = DashboardService.normalize_text(product.product_name)
            if not name:
                continue
            rows[name] = years
        return rows

    @staticmethod
    def product_lookup_keys(asset: Asset) -> list[str]:
        return [DashboardService.normalize_text(asset.name)]

    @staticmethod
    def normalize_text(value: str | None) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def product_matches_asset(product: ProductCatalog, asset: Asset) -> bool:
        return DashboardService.normalize_text(product.product_name) == DashboardService.normalize_text(asset.name)

    @staticmethod
    def retirement_month_trend(assets: list[Asset], products: list[ProductCatalog], now: datetime) -> list[int]:
        soon = DashboardService.retirement_soon_assets(assets, products, now)
        months = DashboardService.last_months(5, now)
        return [sum(1 for item in soon if DashboardService.in_month(datetime.fromisoformat(item["retirement_date"]), month)) for month in months]

    @staticmethod
    def retirement_due_trend(assets: list[Asset], products: list[ProductCatalog], now: datetime) -> dict:
        rows = []
        for asset in assets:
            date = DashboardService.resolve_warranty_or_retirement_date(asset, products)
            if date:
                rows.append(date)
        months = DashboardService.next_months(6, now)
        return {
            "months": [DashboardService.month_label(month) for month in months],
            "due": [sum(1 for date in rows if DashboardService.in_month(date, month)) for month in months],
            "overdue": sum(1 for date in rows if date.date() < now.date()),
        }

    @staticmethod
    def repair_dashboard(db: Session, user_context: dict | None) -> dict:
        query = db.query(RepairRecord).outerjoin(Asset, Asset.asset_id == RepairRecord.asset_id)
        query = RepairServiceProxy.apply_data_scope(query, user_context)
        top_faults = query.with_entities(RepairRecord.fault_reason, func.count(RepairRecord.id)).group_by(RepairRecord.fault_reason).order_by(func.count(RepairRecord.id).desc()).limit(10).all()
        total_cost = query.with_entities(func.coalesce(func.sum(RepairRecord.repair_cost), 0)).scalar() or 0
        return {"topFaults": [{"name": name or "未填写", "count": int(count or 0)} for name, count in top_faults], "totalCost": float(total_cost), "total": query.count()}

    @staticmethod
    def maintenance(repair_dashboard: dict, assets: list[Asset]) -> dict:
        repair_assets = [asset for asset in assets if asset.status == "repair"]
        return {
            "top10": repair_dashboard["topFaults"] or [{"name": asset.name, "count": 1} for asset in repair_assets[:10]],
            "mttr": "待完工统计" if repair_dashboard["total"] else "0小时",
            "monthCost": repair_dashboard["totalCost"],
            "yearCost": repair_dashboard["totalCost"],
        }

    @staticmethod
    def personnel_trend(users: list[UserDirectory], now: datetime) -> dict:
        months = DashboardService.last_months(6, now)
        business_users = [user for user in users if user.role not in {"admin", "auditor"} and str(user.username or "").lower() not in {"admin", "auditor"}]
        onboarding = [sum(1 for user in business_users if DashboardService.in_month(user.created_at, month)) for month in months]
        inactive_users = [user for user in business_users if str(user.status or "").lower() in DashboardService.INACTIVE_USER_STATUSES]
        offboarding = [sum(1 for user in inactive_users if DashboardService.in_month(user.last_synced_at or user.created_at, month)) for month in months]
        return {
            "months": [DashboardService.month_label(month) for month in months],
            "onboarding": onboarding,
            "offboarding": offboarding,
            "activeTotal": len([user for user in business_users if user not in inactive_users]),
            "inactiveTotal": len(inactive_users),
            "onboardingTotal": sum(onboarding),
            "offboardingTotal": sum(offboarding),
        }

    @staticmethod
    def recent_records(lifecycles: list[Lifecycle], assets: list[Asset]) -> list[dict]:
        asset_map = {asset.asset_id: asset for asset in assets}
        rows = []
        for item in lifecycles:
            if item.to_status not in {"in_stock", "in_use", "borrowed", "out_stock"}:
                continue
            asset = asset_map.get(item.asset_id)
            rows.append({
                "asset_id": item.asset_id,
                "user": item.operator or (asset.owner_user_id if asset else "-") or "-",
                "asset": asset.name if asset else item.asset_id,
                "type": asset.category if asset else "-",
                "time": item.timestamp.date().isoformat() if item.timestamp else "-",
                "action": "归还" if item.to_status == "in_stock" else "领用",
            })
            if len(rows) >= 6:
                break
        return rows

    @staticmethod
    def warranty_rows(retirement_assets: list[dict]) -> list[dict]:
        return [
            {
                "name": item["name"],
                "type": "硬件维保",
                "date": item["retirement_date"],
                "days": max(int(item["days_remaining"]), 0),
                "status": "已过保" if item["overdue"] else "即将到期" if item["days_remaining"] <= 30 else "正常",
            }
            for item in retirement_assets[:6]
        ]


class RepairServiceProxy:
    @staticmethod
    def apply_data_scope(query, user_context: dict | None):
        if can_view_all_data(user_context):
            return query
        dept_id = scoped_dept_id(user_context)
        identities = scoped_user_identities(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter(Asset.dept_id == dept_id)
        if identities:
            return query.filter(Asset.owner_user_id.in_(identities))
        return query.filter(False)
