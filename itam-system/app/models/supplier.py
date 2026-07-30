from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier_no = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    contact = Column(String(128), nullable=True)
    phone = Column(String(64), nullable=True)
    level = Column(String(32), default="普通", nullable=False)
    status = Column(String(32), default="启用", nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
