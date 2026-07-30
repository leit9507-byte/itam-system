from sqlalchemy import Column, Integer, Numeric, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class ScrapRequest(Base):
    __tablename__ = "scrap_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_no = Column(String(64), unique=True, nullable=False, index=True)
    retirement_flow_no = Column(String(64), nullable=True, index=True)
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
    purchase_price = Column(Numeric(12, 2, asdecimal=False), default=0)
    purchase_date = Column(UTCDateTime, nullable=True)
    purchase_approval_no = Column(String(128), nullable=True)
    purchase_supplier_name = Column(String(128), nullable=True)
    applicant = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    disposal_method = Column(String(64), nullable=True)
    retirement_date = Column(UTCDateTime, nullable=True)
    retirement_approval_no = Column(String(128), nullable=True)
    estimated_residual_value = Column(Numeric(12, 2, asdecimal=False), default=0)
    final_residual_value = Column(Numeric(12, 2, asdecimal=False), default=0)
    disposal_remark = Column(Text, nullable=True)
    dispose_recipient_user_id = Column(String(128), nullable=True)
    dispose_recipient_name = Column(String(128), nullable=True)
    disposed_by = Column(String(128), nullable=True)
    disposed_at = Column(UTCDateTime, nullable=True)
    status = Column(String(32), default="待处置", nullable=False, index=True)
    approver = Column(String(128), nullable=True)
    approved_at = Column(UTCDateTime, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
