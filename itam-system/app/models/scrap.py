from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.core.database import Base


class ScrapRequest(Base):
    __tablename__ = "scrap_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_no = Column(String(64), unique=True, nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    asset_name = Column(String(128), nullable=False)
    asset_sn = Column(String(128), nullable=True)
    company = Column(String(128), nullable=True)
    category = Column(String(64), nullable=True)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    owner_user_id = Column(String(64), nullable=True)
    dept_id = Column(String(64), nullable=True)
    location = Column(String(128), nullable=True)
    purchase_price = Column(Float, default=0)
    purchase_date = Column(DateTime, nullable=True)
    purchase_approval_no = Column(String(128), nullable=True)
    purchase_supplier_name = Column(String(128), nullable=True)
    applicant = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    disposal_method = Column(String(64), nullable=True)
    estimated_residual_value = Column(Float, default=0)
    status = Column(String(32), default="审批中", nullable=False, index=True)
    approver = Column(String(128), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
