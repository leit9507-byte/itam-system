from sqlalchemy import Column, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_by = Column(String(128), nullable=True)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
