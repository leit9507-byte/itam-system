import math
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.system_setting_service import SystemSettingService


class AssetResidualService:
    DAYS_PER_YEAR = 365.2425
    VALID_MISSING_BASIS_POLICIES = {"original", "zero"}
    VALID_METHODS = {"straight_line", "double_declining", "sum_of_years_digits", "fixed_rate"}
    DEFAULT_FIXED_RATE_VALUE = 0.5

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
        if data.get("method") not in AssetResidualService.VALID_METHODS:
            data["method"] = "straight_line"
        data["minimum_residual_rate"] = AssetResidualService.clamp_rate(data.get("minimum_residual_rate"))
        fixed_rate_value = data.get("fixed_rate_value")
        data["fixed_rate_value"] = (
            AssetResidualService.clamp_rate(fixed_rate_value)
            if fixed_rate_value is not None
            else AssetResidualService.DEFAULT_FIXED_RATE_VALUE
        )
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
        result = SystemSettingService.save_json(db, SystemSettingService.ASSET_RESIDUAL_KEY, normalized, operator)
        from app.services.dashboard_service import DashboardService

        DashboardService.invalidate()
        return result

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
        residual_rate = AssetResidualService.residual_rate_for_category(config, category)
        minimum_value = original_value * residual_rate
        method = config.get("method", "straight_line")
        if method == "fixed_rate":
            if not purchase_date:
                return round(original_value if config.get("missing_basis_policy") == "original" else 0, 2)
            start_date = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
            current = as_of or date.today()
            current_date = current.date() if isinstance(current, datetime) else current
            elapsed_days = max((current_date - start_date).days, 0)
            elapsed_years = elapsed_days / AssetResidualService.DAYS_PER_YEAR
            rate = AssetResidualService.clamp_rate(config.get("fixed_rate_value"))
            current_value = original_value * ((1 - rate) ** elapsed_years)
            return round(max(minimum_value, min(current_value, original_value)), 2)

        if not purchase_date or useful_years <= 0:
            return round(original_value if config.get("missing_basis_policy") == "original" else 0, 2)

        start_date = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
        current = as_of or date.today()
        current_date = current.date() if isinstance(current, datetime) else current
        elapsed_days = max((current_date - start_date).days, 0)
        elapsed_years = min(elapsed_days / AssetResidualService.DAYS_PER_YEAR, useful_years)
        progress = min(elapsed_years / useful_years, 1)
        if progress >= 1:
            return round(minimum_value, 2)
        depreciable_value = original_value - minimum_value
        if method == "double_declining":
            annual_rate = min(2 / useful_years, 1)
            current_value = original_value * ((1 - annual_rate) ** elapsed_years)
        elif method == "sum_of_years_digits":
            depreciation_fraction = AssetResidualService.sum_of_years_depreciation_fraction(elapsed_years, useful_years)
            current_value = original_value - (depreciable_value * depreciation_fraction)
        else:
            current_value = original_value - (depreciable_value * progress)
        return round(max(minimum_value, current_value), 2)

    @staticmethod
    def sum_of_years_depreciation_fraction(elapsed_years: float, useful_years: float) -> float:
        periods = max(int(math.ceil(useful_years)), 1)
        denominator = periods * (periods + 1) / 2
        capped_elapsed = min(max(float(elapsed_years), 0), useful_years)
        full_years = min(int(math.floor(capped_elapsed)), periods)
        weighted_years = sum(periods - index for index in range(full_years))
        fraction = capped_elapsed - full_years
        if full_years < periods and fraction > 0:
            weighted_years += (periods - full_years) * fraction
        return min(weighted_years / denominator, 1)

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
