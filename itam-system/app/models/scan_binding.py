from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class AssetScanBinding(Base):
    __tablename__ = "asset_scan_bindings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(64), nullable=False, index=True)
    scan_key = Column(String(255), nullable=False, unique=True, index=True)
    scan_raw = Column(Text, nullable=False)
    scan_type = Column(String(64), nullable=False, default="generic")
    status = Column(String(32), nullable=False, default="active", index=True)
    remark = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
