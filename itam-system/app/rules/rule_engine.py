from datetime import datetime, timedelta
from itertools import groupby

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.asset import Asset
from app.models.lifecycle import Lifecycle


class RuleEngine:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def run(self) -> list[dict]:
        assets = self.db.query(Asset).all()
        violations: list[dict] = []
        violations.extend(self._user_asset_count_limit(assets))
        violations.extend(self._idle_assets_over_threshold(assets))
        violations.extend(self._high_value_without_dept(assets))
        violations.extend(self._single_owner_value_limit(assets))
        return violations

    def _user_asset_count_limit(self, assets: list[Asset]) -> list[dict]:
        violations = []
        owned_assets = sorted([asset for asset in assets if asset.owner_user_id], key=lambda item: item.owner_user_id)
        for owner, group in groupby(owned_assets, key=lambda item: item.owner_user_id):
            user_assets = list(group)
            if len(user_assets) > self.settings.max_assets_per_user:
                for asset in user_assets:
                    violations.append(
                        {
                            "asset_id": asset.asset_id,
                            "rule": "USER_ASSET_COUNT_LIMIT",
                            "severity": "medium",
                            "message": f"用户 {owner} 名下资产数量 {len(user_assets)} 超过阈值 {self.settings.max_assets_per_user}",
                        }
                    )
        return violations

    def _idle_assets_over_threshold(self, assets: list[Asset]) -> list[dict]:
        violations = []
        cutoff = datetime.utcnow() - timedelta(days=self.settings.idle_days_threshold)
        idle_assets = [asset for asset in assets if asset.status in {"idle", "in_stock"}]

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
                        "severity": "low",
                        "message": f"资产闲置超过 {self.settings.idle_days_threshold} 天",
                    }
                )
        return violations

    def _high_value_without_dept(self, assets: list[Asset]) -> list[dict]:
        return [
            {
                "asset_id": asset.asset_id,
                "rule": "HIGH_VALUE_WITHOUT_DEPT",
                "severity": "high",
                "message": f"高价值资产未绑定部门，资产价值 {asset.purchase_price}",
            }
            for asset in assets
            if asset.purchase_price >= self.settings.high_value_threshold and not asset.dept_id
        ]

    def _single_owner_value_limit(self, assets: list[Asset]) -> list[dict]:
        violations = []
        owned_assets = sorted([asset for asset in assets if asset.owner_user_id], key=lambda item: item.owner_user_id)
        for owner, group in groupby(owned_assets, key=lambda item: item.owner_user_id):
            user_assets = list(group)
            total_value = sum(asset.purchase_price or 0 for asset in user_assets)
            threshold = self.settings.high_value_threshold * 2
            if total_value > threshold:
                for asset in user_assets:
                    violations.append(
                        {
                            "asset_id": asset.asset_id,
                            "rule": "SINGLE_OWNER_VALUE_LIMIT",
                            "severity": "high",
                            "message": f"用户 {owner} 名下资产总值 {total_value} 超过阈值 {threshold}",
                        }
                    )
        return violations
