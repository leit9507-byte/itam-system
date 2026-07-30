from app.core.time import TimezoneModel

from datetime import datetime

from pydantic import ConfigDict, Field


class NotificationSettingSave(TimezoneModel):
    enabled: bool = False
    webhook_url: str | None = None
    secret: str | None = None
    event_types: dict[str, bool] = Field(default_factory=dict)


class NotificationSettingOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    enabled: bool
    webhook_url: str | None
    secret: str | None
    event_types: dict[str, bool] | None
    last_test_status: str | None
    last_test_message: str | None
    updated_at: datetime


class NotificationTestRequest(TimezoneModel):
    message: str = Field(default="资产管理系统消息通知测试")
