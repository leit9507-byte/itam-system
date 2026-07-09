from functools import lru_cache
from pydantic import BaseModel
import os
from urllib.parse import quote_plus


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def build_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST")
    if not host:
        return "sqlite:///./itam.db"
    port = os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or "3306"
    database = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "itam_system"
    user = os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "itam"
    password = quote_plus(os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or "")
    charset = os.getenv("DB_CHARSET", "utf8mb4")
    return f"mysql+pymysql://{quote_plus(user)}:{password}@{host}:{port}/{database}?charset={charset}"


class Settings(BaseModel):
    app_name: str = "Enterprise ITAM System"
    database_url: str = build_database_url()
    db_pool_size: int = env_int("DB_POOL_SIZE", "10")
    db_max_overflow: int = env_int("DB_MAX_OVERFLOW", "20")
    db_pool_recycle: int = env_int("DB_POOL_RECYCLE", "1800")
    db_pool_timeout: int = env_int("DB_POOL_TIMEOUT", "30")
    db_connect_timeout: int = env_int("DB_CONNECT_TIMEOUT", "10")
    db_charset: str = os.getenv("DB_CHARSET", "utf8mb4")
    db_timezone: str = os.getenv("DB_TIMEZONE", "+08:00")
    db_echo: bool = env_bool("DB_ECHO", "false")
    audit_report_path: str = os.getenv("AUDIT_REPORT_PATH", "audit_report.html")
    max_assets_per_user: int = int(os.getenv("MAX_ASSETS_PER_USER", "5"))
    high_value_threshold: float = float(os.getenv("HIGH_VALUE_THRESHOLD", "50000"))
    idle_days_threshold: int = int(os.getenv("IDLE_DAYS_THRESHOLD", "90"))
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    login_lock_threshold: int = int(os.getenv("LOGIN_LOCK_THRESHOLD", "5"))
    login_lock_minutes: int = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    cors_origins: list[str] = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",") if item.strip()]
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    allowed_upload_extensions: set[str] = {
        item.strip().lower()
        for item in os.getenv(
            "ALLOWED_UPLOAD_EXTENSIONS",
            ".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip",
        ).split(",")
        if item.strip()
    }
    production_mode: bool = os.getenv("APP_ENV", "development").lower() in {"prod", "production"}
    initial_admin_password: str | None = os.getenv("INITIAL_ADMIN_PASSWORD")
    initial_auditor_password: str | None = os.getenv("INITIAL_AUDITOR_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    return Settings()
