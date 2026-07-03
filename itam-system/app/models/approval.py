from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.core.database import Base


class ApprovalRule(Base):
    __tablename__ = "approval_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flow_type = Column(String(32), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    min_amount = Column(Float, nullable=True)
    max_amount = Column(Float, nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    approver_role = Column(String(64), nullable=True)
    approver_user_id = Column(String(64), nullable=True)
    level = Column(Integer, default=1, nullable=False, index=True)
    require_all = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
