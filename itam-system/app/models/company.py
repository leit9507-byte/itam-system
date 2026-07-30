from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    code = Column(String(64), nullable=True, index=True)
    contact = Column(String(128), nullable=True)
    status = Column(String(32), default="启用", nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
