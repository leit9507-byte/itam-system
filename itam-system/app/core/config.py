from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "Enterprise ITAM System"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./itam.db")
    audit_report_path: str = os.getenv("AUDIT_REPORT_PATH", "audit_report.html")
    max_assets_per_user: int = int(os.getenv("MAX_ASSETS_PER_USER", "5"))
    high_value_threshold: float = float(os.getenv("HIGH_VALUE_THRESHOLD", "50000"))
    idle_days_threshold: int = int(os.getenv("IDLE_DAYS_THRESHOLD", "90"))
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    login_lock_threshold: int = int(os.getenv("LOGIN_LOCK_THRESHOLD", "5"))
    login_lock_minutes: int = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")


@lru_cache
def get_settings() -> Settings:
    return Settings()
