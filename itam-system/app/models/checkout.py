from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class AssetCheckout(Base):
    __tablename__ = "asset_checkouts"
    __table_args__ = (UniqueConstraint("asset_id", "open_token", name="uq_asset_checkouts_single_open"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=False, index=True)
    checkout_type = Column(String(32), nullable=False, index=True)
    assignee_user_id = Column(String(64), nullable=True, index=True)
    assignee_name = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True)
    due_date = Column(UTCDateTime, nullable=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    # NULL is used for closed rows so the unique constraint only guards the current open checkout.
    open_token = Column(String(8), nullable=True, default="open")
    checked_out_at = Column(UTCDateTime, default=utc_now, nullable=False)
    checked_out_by = Column(String(64), nullable=False, default="system")
    checked_in_at = Column(UTCDateTime, nullable=True)
    checked_in_by = Column(String(64), nullable=True)
    checkin_location = Column(String(128), nullable=True)
    remark = Column(Text, nullable=True)
    checkin_remark = Column(Text, nullable=True)
