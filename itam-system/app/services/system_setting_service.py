import json
from copy import deepcopy
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.system_setting import SystemSetting


class SystemSettingService:
    ASSET_RESIDUAL_KEY = "asset_residual_config"
    DEFAULT_ASSET_RESIDUAL_CONFIG = {
        "method": "straight_line",
        "minimum_residual_rate": 0.05,
        "missing_basis_policy": "original",
        "category_rates": [],
    }

    @staticmethod
    def default_asset_residual_config() -> dict:
        return deepcopy(SystemSettingService.DEFAULT_ASSET_RESIDUAL_CONFIG)

    @staticmethod
    def get_json(db: Session, key: str, default: dict | None = None) -> dict:
        row = db.get(SystemSetting, key)
        if not row:
            return deepcopy(default or {})
        try:
            data = json.loads(row.value or "{}")
        except json.JSONDecodeError:
            return deepcopy(default or {})
        return data if isinstance(data, dict) else deepcopy(default or {})

    @staticmethod
    def save_json(db: Session, key: str, value: dict, operator: str = "system") -> dict:
        row = db.get(SystemSetting, key)
        if not row:
            row = SystemSetting(key=key)
            db.add(row)
        row.value = json.dumps(value, ensure_ascii=False)
        row.updated_by = operator
        row.updated_at = utc_now()
        db.commit()
        return value
