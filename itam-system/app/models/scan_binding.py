from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
