from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class RepairRecord(Base):
    __tablename__ = "repair_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repair_no = Column(String(64), unique=True, nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    repair_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    fault_reason = Column(String(512), nullable=False)
    repair_cost = Column(Float, default=0, nullable=False)
    vendor = Column(String(128), nullable=True)
    operator = Column(String(64), default="资产管理员", nullable=False)
    status = Column(String(32), default="维修中", nullable=False, index=True)
    finish_time = Column(DateTime, nullable=True)
    remark = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
