from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.system_setting_service import SystemSettingService


class AssetResidualService:
    DAYS_PER_YEAR = 365.2425
    VALID_MISSING_BASIS_POLICIES = {"original", "zero"}

    @staticmethod
    def get_config(db: Session | None = None) -> dict:
        config = SystemSettingService.default_asset_residual_config()
        if db:
            config.update(SystemSettingService.get_json(db, SystemSettingService.ASSET_RESIDUAL_KEY, config))
        if "minimum_residual_rate" not in config:
            config["minimum_residual_rate"] = get_settings().asset_residual_rate
        return AssetResidualService.normalize_config(config)

    @staticmethod
    def normalize_config(config: dict | None) -> dict:
        data = SystemSettingService.default_asset_residual_config()
        data.update(config or {})
        data["method"] = "straight_line"
        data["minimum_residual_rate"] = AssetResidualService.clamp_rate(data.get("minimum_residual_rate"))
        if data.get("missing_basis_policy") not in AssetResidualService.VALID_MISSING_BASIS_POLICIES:
            data["missing_basis_policy"] = "original"
        category_rates = []
        seen = set()
        for item in data.get("category_rates") or []:
            category = str(item.get("category") or "").strip()
            if not category or category in seen:
                continue
            seen.add(category)
            category_rates.append({"category": category, "minimum_residual_rate": AssetResidualService.clamp_rate(item.get("minimum_residual_rate"))})
        data["category_rates"] = category_rates
        return data

    @staticmethod
    def save_config(db: Session, config: dict, operator: str = "system") -> dict:
        normalized = AssetResidualService.normalize_config(config)
        if normalized["method"] != "straight_line":
            raise ValueError("当前仅支持直线折旧法")
        return SystemSettingService.save_json(db, SystemSettingService.ASSET_RESIDUAL_KEY, normalized, operator)

    @staticmethod
    def clamp_rate(value) -> float:
        try:
            return min(max(float(value), 0), 1)
        except (TypeError, ValueError):
            return 0.05

    @staticmethod
    def calculate(
        purchase_price: float | None,
        purchase_date: date | datetime | None,
        retirement_years: int | float | None,
        as_of: date | datetime | None = None,
        config: dict | None = None,
        category: str | None = None,
    ) -> float:
        config = AssetResidualService.normalize_config(config or {"minimum_residual_rate": get_settings().asset_residual_rate})
        original_value = max(float(purchase_price or 0), 0)
        if original_value == 0:
            return 0.0

        try:
            useful_years = float(retirement_years or 0)
        except (TypeError, ValueError):
            useful_years = 0
        if not purchase_date or useful_years <= 0:
            return round(original_value if config.get("missing_basis_policy") == "original" else 0, 2)

        start_date = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
        current = as_of or date.today()
        current_date = current.date() if isinstance(current, datetime) else current
        elapsed_days = max((current_date - start_date).days, 0)
        progress = min(elapsed_days / (useful_years * AssetResidualService.DAYS_PER_YEAR), 1)

        residual_rate = AssetResidualService.residual_rate_for_category(config, category)
        minimum_value = original_value * residual_rate
        current_value = original_value - ((original_value - minimum_value) * progress)
        return round(max(minimum_value, current_value), 2)

    @staticmethod
    def residual_rate_for_category(config: dict, category: str | None = None) -> float:
        for item in config.get("category_rates") or []:
            if item.get("category") == category:
                return AssetResidualService.clamp_rate(item.get("minimum_residual_rate"))
        return AssetResidualService.clamp_rate(config.get("minimum_residual_rate"))

    @staticmethod
    def calculate_asset(asset, as_of: date | datetime | None = None, db: Session | None = None, residual_config: dict | None = None) -> float:
        config = asset.config or {}
        return AssetResidualService.calculate(
            asset.purchase_price,
            asset.purchase_date,
            config.get("retirement_years"),
            as_of,
            residual_config or AssetResidualService.get_config(db),
            asset.category,
        )
