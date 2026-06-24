from datetime import datetime, timedelta
from itertools import groupby

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.asset import Asset
from app.models.audit_rule import AuditRule
from app.models.lifecycle import Lifecycle


class RuleEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def run(self) -> list[dict]:
        assets = self.db.query(Asset).all()
        rules = self._rules_by_code()
        violations: list[dict] = []
        violations.extend(self._user_asset_count_limit(assets, rules["USER_ASSET_COUNT_LIMIT"]))
        violations.extend(self._idle_assets_over_threshold(assets, rules["ASSET_IDLE_OVER_90_DAYS"]))
        violations.extend(self._high_value_without_dept(assets, rules["HIGH_VALUE_WITHOUT_DEPT"]))
        violations.extend(self._single_owner_value_limit(assets, rules["SINGLE_OWNER_VALUE_LIMIT"]))
        return violations

    def _rules_by_code(self) -> dict[str, dict]:
        rules = {
            "USER_ASSET_COUNT_LIMIT": {
                "name": "用户资产数量超限",
                "severity": "medium",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.max_assets_per_user),
                "threshold_days": None,
            },
            "ASSET_IDLE_OVER_90_DAYS": {
                "name": "资产闲置超期",
                "severity": "low",
                "enabled": True,
                "scope_category": "",
                "threshold_value": None,
                "threshold_days": self.settings.idle_days_threshold,
            },
            "HIGH_VALUE_WITHOUT_DEPT": {
                "name": "高价值资产未绑定部门",
                "severity": "high",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.high_value_threshold),
                "threshold_days": None,
            },
            "SINGLE_OWNER_VALUE_LIMIT": {
                "name": "单人资产价值超标",
                "severity": "high",
                "enabled": True,
                "scope_category": "",
                "threshold_value": float(self.settings.high_value_threshold * 2),
                "threshold_days": None,
            },
        }
        for item in self.db.query(AuditRule).all():
            base = rules.get(item.rule_code, {})
            rules[item.rule_code] = {
                "name": item.name or base.get("name", item.rule_code),
                "severity": item.severity or base.get("severity", "medium"),
                "enabled": item.enabled,
                "scope_category": item.scope_category or "",
                "threshold_value": item.threshold_value if item.threshold_value is not None else base.get("threshold_value"),
                "threshold_days": item.threshold_days if item.threshold_days is not None else base.get("threshold_days"),
            }
        return rules

    def _category_assets(self, assets: list[Asset], category: str | None) -> list[Asset]:
        if not category:
            return assets
        return [asset for asset in assets if asset.category == category]

    def _user_asset_count_limit(self, assets: list[Asset], rule: dict) -> list[dict]:
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
            scope_text = f"{scope_category} " if scope_category else ""
            for asset in user_assets:
                violations.append(
                    {
                        "asset_id": asset.asset_id,
                        "rule": "USER_ASSET_COUNT_LIMIT",
                        "severity": rule.get("severity") or "medium",
                        "message": f"用户 {owner} 名下{scope_text}资产数量 {len(user_assets)} 超过阈值 {threshold}",
                    }
                )
        return violations

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
            last_event = (
                self.db.query(Lifecycle)
                .filter(Lifecycle.asset_id == asset.asset_id)
                .order_by(Lifecycle.timestamp.desc())
                .first()
            )
            last_time = last_event.timestamp if last_event else asset.created_at
            if last_time < cutoff:
                violations.append(
                    {
                        "asset_id": asset.asset_id,
                        "rule": "ASSET_IDLE_OVER_90_DAYS",
                        "severity": rule.get("severity") or "low",
                        "message": f"资产闲置超过 {threshold_days} 天",
                    }
                )
        return violations

    def _high_value_without_dept(self, assets: list[Asset], rule: dict) -> list[dict]:
        if not rule.get("enabled"):
            return []
        threshold = float(rule.get("threshold_value") or self.settings.high_value_threshold)
        return [
            {
                "asset_id": asset.asset_id,
                "rule": "HIGH_VALUE_WITHOUT_DEPT",
                "severity": rule.get("severity") or "high",
                "message": f"高价值资产未绑定部门，资产价值 {asset.purchase_price} 超过阈值 {threshold}",
            }
            for asset in self._category_assets(assets, rule.get("scope_category"))
            if asset.purchase_price >= threshold and not asset.dept_id
        ]

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
                    {
                        "asset_id": asset.asset_id,
                        "rule": "SINGLE_OWNER_VALUE_LIMIT",
                        "severity": rule.get("severity") or "high",
                        "message": f"用户 {owner} 名下资产总值 {total_value} 超过阈值 {threshold}",
                    }
                )
        return violations
