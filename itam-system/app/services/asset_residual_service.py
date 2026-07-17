from datetime import date, datetime

from app.core.config import get_settings


class AssetResidualService:
    DAYS_PER_YEAR = 365.2425

    @staticmethod
    def calculate(
        purchase_price: float | None,
        purchase_date: date | datetime | None,
        retirement_years: int | float | None,
        as_of: date | datetime | None = None,
    ) -> float:
        original_value = max(float(purchase_price or 0), 0)
        if original_value == 0:
            return 0.0

        try:
            useful_years = float(retirement_years or 0)
        except (TypeError, ValueError):
            useful_years = 0
        if not purchase_date or useful_years <= 0:
            return round(original_value, 2)

        start_date = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
        current = as_of or date.today()
        current_date = current.date() if isinstance(current, datetime) else current
        elapsed_days = max((current_date - start_date).days, 0)
        progress = min(elapsed_days / (useful_years * AssetResidualService.DAYS_PER_YEAR), 1)

        configured_rate = get_settings().asset_residual_rate
        residual_rate = min(max(float(configured_rate), 0), 1)
        minimum_value = original_value * residual_rate
        current_value = original_value - ((original_value - minimum_value) * progress)
        return round(max(minimum_value, current_value), 2)

    @staticmethod
    def calculate_asset(asset, as_of: date | datetime | None = None) -> float:
        config = asset.config or {}
        return AssetResidualService.calculate(
            asset.purchase_price,
            asset.purchase_date,
            config.get("retirement_years"),
            as_of,
        )
