from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.core.database import Base


class RepairRecord(Base):
    __tablename__ = "repair_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repair_no = Column(String(64), unique=True, nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    repair_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    repair_type = Column(String(64), default="普通维修", nullable=False, index=True)
    fault_reason = Column(String(512), nullable=False)
    repair_cost = Column(Numeric(12, 2, asdecimal=False), default=0, nullable=False)
    vendor = Column(String(128), nullable=True)
    operator = Column(String(64), default="资产管理员", nullable=False)
    status = Column(String(32), default="维修中", nullable=False, index=True)
    repair_result = Column(String(64), nullable=True, index=True)
    finish_time = Column(DateTime, nullable=True)
    remark = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RepairFaultType(Base):
    __tablename__ = "repair_fault_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    enabled = Column(String(16), default="启用", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
