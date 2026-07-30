from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class Lifecycle(Base):
    __tablename__ = "lifecycles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    operator = Column(String(64), nullable=False, default="system")
    remark = Column(Text, nullable=True)
    timestamp = Column(UTCDateTime, default=utc_now, nullable=False, index=True)
