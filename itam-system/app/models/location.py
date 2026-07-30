from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    code = Column(String(64), nullable=True, index=True)
    type = Column(String(64), default="办公位置", nullable=False, index=True)
    owner_dept = Column(String(128), nullable=True)
    description = Column(String(255), nullable=True)
    status = Column(String(32), default="启用", nullable=False, index=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
