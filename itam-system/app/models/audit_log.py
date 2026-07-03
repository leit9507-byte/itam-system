from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class AssetChangeLog(Base):
    __tablename__ = "asset_change_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(64), nullable=False, index=True)
    field_name = Column(String(64), nullable=False, index=True)
    field_label = Column(String(128), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    operator = Column(String(128), nullable=False, default="system", index=True)
    source = Column(String(64), nullable=False, default="asset_update", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OperationAuditLog(Base):
    __tablename__ = "operation_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    module = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    target_type = Column(String(64), nullable=True, index=True)
    target_id = Column(String(128), nullable=True, index=True)
    operator = Column(String(128), nullable=False, default="system", index=True)
    summary = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
