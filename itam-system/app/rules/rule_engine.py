from datetime import datetime, timedelta
from itertools import groupby

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.asset import Asset
from app.models.audit_rule import AuditRule
from app.models.lifecycle import Lifecycle
from app.models.repair import RepairRecord
from app.models.user import UserDirectory


class RuleEngine:
    inactive_user_statuses = {"inactive", "disabled", "locked", "resigned", "left", "offboarded", "离职", "停用", "禁用"}

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def run(self) -> list[dict]:
        assets = self.db.query(Asset).all()
        rules = self._rules_by_code()
        violations: list[dict] = []
        violations.extend(self._user_asset_count_limit(assets, rules["USER_ASSET_COUNT_LIMIT"], "USER_ASSET_COUNT_LIMIT"))
        for code, rule in rules.items():
            if code.startswith("CUSTOM_PERSON_COUNT_"):
                violations.extend(self._user_asset_count_limit(assets, rule, code))
        violations.extend(self._offboarding_assets_not_returned(assets, rules["OFFBOARDING_ASSET_NOT_RETURNED"]))
        violations.extend(self._borrowed_assets_not_returned(assets, rules["BORROWED_ASSET_NOT_RETURNED"]))
        violations.extend(self._single_owner_value_limit(assets, rules["SINGLE_OWNER_VALUE_LIMIT"]))
        violations.extend(self._high_value_purchase(assets, rules["HIGH_VALUE_PURCHASE"]))
        violations.extend(self._idle_assets_over_threshold(assets, rules["ASSET_IDLE_OVER_90_DAYS"]))
        violations.extend(self._asset_retirement_overdue(assets, rules["ASSET_RETIREMENT_OVERDUE"]))
        violations.extend(self._device_fault_audit(assets, rules["DEVICE_FAULT_AUDIT"]))
        return violations

    def _rules_by_code(self) -> dict[str, dict]:
        rules = {
            "USER_ASSET_COUNT_LIMIT": {
                "name": "人员资产数量超配",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.max_assets_per_user),
                "threshold_days": None,
                "audit_scope": "person",
            },
            "OFFBOARDING_ASSET_NOT_RETURNED": {
                "name": "离职人员资产未回收",
                "severity": "high",
                "enabled": True,
                "scope_category": "",
                "threshold_value": None,
                "threshold_days": None,
                "audit_scope": "person",
            },
            "BORROWED_ASSET_NOT_RETURNED": {
                "name": "借用资产超期未回收",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": None,
                "threshold_days": 30,
                "audit_scope": "person",
            },
            "SINGLE_OWNER_VALUE_LIMIT": {
                "name": "人员名下资产价值超标",
                "severity": "high",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.high_value_threshold * 2),
                "threshold_days": None,
                "audit_scope": "person",
            },
            "HIGH_VALUE_PURCHASE": {
                "name": "超价值采购",
                "severity": "high",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.high_value_threshold),
                "threshold_days": None,
                "audit_scope": "asset",
            },
            "ASSET_IDLE_OVER_90_DAYS": {
                "name": "长期闲置",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": None,
                "threshold_days": self.settings.idle_days_threshold,
                "audit_scope": "asset",
            },
            "ASSET_RETIREMENT_OVERDUE": {
                "name": "超期服役审计",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": None,
                "threshold_days": 0,
                "audit_scope": "asset",
            },
            "DEVICE_FAULT_AUDIT": {
                "name": "设备故障审计",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": 2,
                "threshold_days": 180,
                "audit_scope": "asset",
            },
        }
        legacy_aliases = {"HIGH_VALUE_WITHOUT_DEPT": "HIGH_VALUE_PURCHASE"}
        for item in self.db.query(AuditRule).all():
            code = legacy_aliases.get(item.rule_code, item.rule_code)
            base = rules.get(code, {})
            audit_scope = base.get("audit_scope", "asset")
            if code.startswith("CUSTOM_PERSON_COUNT_"):
                audit_scope = "person"
            rules[code] = {
                "name": item.name or base.get("name", code),
                "severity": item.severity or base.get("severity", "medium"),
                "enabled": item.enabled,
                "scope_category": item.scope_category or "",
                "threshold_value": item.threshold_value if item.threshold_value is not None else base.get("threshold_value"),
                "threshold_days": item.threshold_days if item.threshold_days is not None else base.get("threshold_days"),
                "audit_scope": audit_scope,
            }
        return rules

    def _category_assets(self, assets: list[Asset], category: str | None) -> list[Asset]:
        if not category:
            return assets
        categories = {item.strip() for item in str(category).split(",") if item.strip()}
        if not categories:
            return assets
        return [asset for asset in assets if asset.category in categories]

    def _violation(self, asset: Asset, rule_code: str, rule: dict, message: str, target_type: str = "asset") -> dict:
        return {
            "asset_id": asset.asset_id,
            "asset_no": asset.asset_no,
            "rule": rule_code,
            "type": rule.get("name") or rule_code,
            "audit_scope": rule.get("audit_scope", "asset"),
            "target_type": target_type,
            "owner_user_id": asset.owner_user_id,
            "dept_id": asset.dept_id,
            "severity": rule.get("severity") or "medium",
            "message": message,
        }

    def _last_event_time(self, asset: Asset) -> datetime:
        last_event = (
            self.db.query(Lifecycle)
            .filter(Lifecycle.asset_id == asset.asset_id)
            .order_by(Lifecycle.timestamp.desc())
            .first()
        )
        return last_event.timestamp if last_event else asset.created_at

    def _retirement_due_date(self, asset: Asset) -> datetime | None:
        if not asset.purchase_date:
            return None
        config = asset.config or {}
        try:
            years = int(config.get("retirement_years") or 0)
        except (TypeError, ValueError):
            return None
        if years <= 0:
            return None
        try:
            return asset.purchase_date.replace(year=asset.purchase_date.year + years)
        except ValueError:
            return asset.purchase_date.replace(month=2, day=28, year=asset.purchase_date.year + years)

    def _user_asset_count_limit(self, assets: list[Asset], rule: dict, rule_code: str) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold = int(rule.get("threshold_value") or self.settings.max_assets_per_user)
        scope_category = rule.get("scope_category") or ""
        scoped_assets = self._category_assets(assets, scope_category)
        owned_assets = sorted([asset for asset in scoped_assets if asset.owner_user_id], key=lambda item: item.owner_user_id)
        violations = []

        for owner, group in groupby(owned_assets, key=lambda item: item.owner_user_id):
            user_assets = list(group)
            if len(user_assets) <= threshold:
                continue
            scope_text = f"{scope_category.replace(',', '、')} " if scope_category else "全部"
            for asset in user_assets:
                violations.append(
                    self._violation(
                        asset,
                        rule_code,
                        rule,
                        f"人员 {owner} 名下{scope_text}资产数量 {len(user_assets)} 超过阈值 {threshold}",
                        "person",
                    )
                )
        return violations

    def _device_fault_audit(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold = int(rule.get("threshold_value") or 2)
        threshold_days = int(rule.get("threshold_days") or 180)
        cutoff = datetime.utcnow() - timedelta(days=threshold_days)
        asset_map = {asset.asset_id: asset for asset in self._category_assets(assets, rule.get("scope_category"))}
        if not asset_map:
            return []
        records = (
            self.db.query(RepairRecord)
            .filter(RepairRecord.asset_id.in_(asset_map.keys()), RepairRecord.created_at >= cutoff)
            .order_by(RepairRecord.asset_id.asc(), RepairRecord.created_at.desc())
            .all()
        )
        grouped: dict[str, list[RepairRecord]] = {}
        for record in records:
            grouped.setdefault(record.asset_id, []).append(record)
        violations = []
        risky_results = {"未修好", "在保送修"}
        for asset_id, rows in grouped.items():
            risky_rows = [row for row in rows if row.repair_result in risky_results or row.status in risky_results]
            if len(rows) < threshold and not risky_rows:
                continue
            asset = asset_map.get(asset_id)
            if not asset:
                continue
            latest = rows[0]
            reason = latest.fault_reason or "未填写故障原因"
            message = f"近 {threshold_days} 天维修 {len(rows)} 次，最近故障：{reason}"
            if risky_rows:
                message = f"{message}；存在未修好或在保送修记录，建议复核是否报废、换新或供应商质保处理"
            violations.append(self._violation(asset, "DEVICE_FAULT_AUDIT", rule, message))
        return violations

    def _asset_retirement_overdue(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        grace_days = int(rule.get("threshold_days") or 0)
        active_statuses = {"in_use", "borrowed", "out_stock", "repair"}
        today = datetime.utcnow()
        violations = []
        for asset in self._category_assets(assets, rule.get("scope_category")):
            if asset.status not in active_statuses:
                continue
            due_date = self._retirement_due_date(asset)
            if not due_date:
                continue
            overdue_days = (today.date() - due_date.date()).days
            if overdue_days <= grace_days:
                continue
            years = int((asset.config or {}).get("retirement_years") or 0)
            owner = asset.owner_user_id or asset.location or "未分配"
            message = f"预计服役 {years} 年，退役日期 {due_date.date().isoformat()}，已超期 {overdue_days} 天；当前状态 {asset.status}，责任/位置：{owner}"
            violations.append(self._violation(asset, "ASSET_RETIREMENT_OVERDUE", rule, message))
        return violations

    def _offboarding_assets_not_returned(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        users = {user.user_id: user for user in self.db.query(UserDirectory).all()}
        risky_statuses = {"in_use", "borrowed", "out_stock"}
        violations = []
        for asset in self._category_assets(assets, rule.get("scope_category")):
            user = users.get(asset.owner_user_id or "")
            if not user or asset.status not in risky_statuses:
                continue
            if (user.status or "").lower() in self.inactive_user_statuses:
                violations.append(
                    self._violation(
                        asset,
                        "OFFBOARDING_ASSET_NOT_RETURNED",
                        rule,
                        f"责任人 {user.display_name} 状态为 {user.status}，资产仍未入库回收",
                        "person",
                    )
                )
        return violations

    def _borrowed_assets_not_returned(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold_days = int(rule.get("threshold_days") or 30)
        cutoff = datetime.utcnow() - timedelta(days=threshold_days)
        violations = []
        for asset in self._category_assets(assets, rule.get("scope_category")):
            if asset.status != "borrowed":
                continue
            last_time = self._last_event_time(asset)
            if last_time < cutoff:
                violations.append(
                    self._violation(
                        asset,
                        "BORROWED_ASSET_NOT_RETURNED",
                        rule,
                        f"借用资产超过 {threshold_days} 天未回收入库",
                        "person",
                    )
                )
        return violations

    def _single_owner_value_limit(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold = float(rule.get("threshold_value") or self.settings.high_value_threshold * 2)
        owned_assets = sorted(
            [asset for asset in self._category_assets(assets, rule.get("scope_category")) if asset.owner_user_id],
            key=lambda item: item.owner_user_id,
        )
        violations = []

        for owner, group in groupby(owned_assets, key=lambda item: item.owner_user_id):
            user_assets = list(group)
            total_value = sum(asset.purchase_price or 0 for asset in user_assets)
            if total_value <= threshold:
                continue
            for asset in user_assets:
                violations.append(
                    self._violation(
                        asset,
                        "SINGLE_OWNER_VALUE_LIMIT",
                        rule,
                        f"人员 {owner} 名下资产总值 {total_value:.0f} 超过阈值 {threshold:.0f}",
                        "person",
                    )
                )
        return violations

    def _high_value_purchase(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold = float(rule.get("threshold_value") or self.settings.high_value_threshold)
        return [
            self._violation(
                asset,
                "HIGH_VALUE_PURCHASE",
                rule,
                f"资产采购原值 {asset.purchase_price or 0:.0f} 超过阈值 {threshold:.0f}，需复核采购审批与供应商信息",
            )
            for asset in self._category_assets(assets, rule.get("scope_category"))
            if (asset.purchase_price or 0) >= threshold
        ]

    def _idle_assets_over_threshold(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold_days = int(rule.get("threshold_days") or self.settings.idle_days_threshold)
        cutoff = datetime.utcnow() - timedelta(days=threshold_days)
        idle_assets = [
            asset
            for asset in self._category_assets(assets, rule.get("scope_category"))
            if asset.status in {"idle", "in_stock"}
        ]
        violations = []

        for asset in idle_assets:
            last_time = self._last_event_time(asset)
            if last_time < cutoff:
                violations.append(
                    self._violation(
                        asset,
                        "ASSET_IDLE_OVER_90_DAYS",
                        rule,
                        f"资产闲置超过 {threshold_days} 天，建议调拨、回收或报废",
                    )
                )
        return violations
