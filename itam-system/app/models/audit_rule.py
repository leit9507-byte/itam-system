from sqlalchemy import Boolean, Column, Float, Integer, String

from app.core.database import Base


class AuditRule(Base):
    __tablename__ = "audit_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    severity = Column(String(16), nullable=False, default="medium")
    scope_category = Column(String(64), nullable=True)
    threshold_value = Column(Float, nullable=True)
    threshold_days = Column(Integer, nullable=True)
    enabled = Column(Boolean, default=True)
