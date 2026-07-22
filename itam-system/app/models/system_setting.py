from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_by = Column(String(128), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
