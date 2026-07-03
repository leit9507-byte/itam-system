from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from app.core.database import Base


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(64), default="feishu_webhook", nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(512), nullable=True)
    secret = Column(String(255), nullable=True)
    event_types = Column(JSON, nullable=True)
    last_test_status = Column(String(32), nullable=True)
    last_test_message = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
