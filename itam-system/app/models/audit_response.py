from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class AuditResponse(Base):
    __tablename__ = "audit_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    violation_key = Column(String(255), unique=True, nullable=False, index=True)
    asset_id = Column(String(64), nullable=True, index=True)
    rule_code = Column(String(64), nullable=False, index=True)
    audit_scope = Column(String(32), nullable=False, default="asset")
    decision = Column(String(32), nullable=False, default="pending")
    reason = Column(Text, nullable=True)
    responder = Column(String(128), nullable=True)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
