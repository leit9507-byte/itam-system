from datetime import date, datetime, time, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, model_validator
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_today() -> date:
    return utc_now().date()


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def app_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=app_timezone())
    return value.astimezone(UTC)


def utc_naive(value: datetime | None = None) -> datetime:
    return ensure_utc(value or utc_now()).replace(tzinfo=None)


@lru_cache
def app_timezone() -> ZoneInfo:
    timezone_name = get_settings().app_timezone
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Invalid APP_TIMEZONE: {timezone_name}") from exc


def app_now() -> datetime:
    return utc_now().astimezone(app_timezone())


def app_today() -> date:
    return app_now().date()


def to_app_timezone(value: datetime) -> datetime:
    return ensure_utc(value).astimezone(app_timezone())


def app_day_bounds(day: date | datetime) -> tuple[datetime, datetime]:
    target_date = day.date() if isinstance(day, datetime) else day
    start = datetime.combine(target_date, time.min, tzinfo=app_timezone())
    end = datetime.combine(target_date, time.max, tzinfo=app_timezone())
    return start.astimezone(UTC), end.astimezone(UTC)


def app_end_of_day(value: datetime) -> datetime:
    local_value = app_datetime_to_utc(value).astimezone(app_timezone())
    return local_value.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(UTC)


def format_app_datetime(value: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return to_app_timezone(value or utc_now()).strftime(fmt)


def _normalize_datetime_values(value):
    if isinstance(value, datetime):
        return app_datetime_to_utc(value)
    if isinstance(value, list):
        return [_normalize_datetime_values(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_datetime_values(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize_datetime_values(item) for key, item in value.items()}
    return value


class TimezoneModel(BaseModel):
    """Interpret timezone-free API datetimes in APP_TIMEZONE and normalize to UTC."""

    @model_validator(mode="after")
    def normalize_datetimes_to_utc(self):
        for field_name in type(self).model_fields:
            value = getattr(self, field_name, None)
            normalized = _normalize_datetime_values(value)
            if normalized is not value:
                object.__setattr__(self, field_name, normalized)
        return self


class UTCDateTime(TypeDecorator):
    """Store UTC as naive DATETIME and expose timezone-aware UTC values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return utc_naive(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return ensure_utc(value)
