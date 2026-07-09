from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base


class AssetCheckout(Base):
    __tablename__ = "asset_checkouts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=False, index=True)
    checkout_type = Column(String(32), nullable=False, index=True)
    assignee_user_id = Column(String(64), nullable=True, index=True)
    assignee_name = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    checked_out_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    checked_out_by = Column(String(64), nullable=False, default="system")
    checked_in_at = Column(DateTime, nullable=True)
    checked_in_by = Column(String(64), nullable=True)
    checkin_location = Column(String(128), nullable=True)
    remark = Column(Text, nullable=True)
    checkin_remark = Column(Text, nullable=True)
