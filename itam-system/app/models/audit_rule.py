from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base


class AuditRule(Base):
    __tablename__ = "audit_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    severity = Column(String(16), nullable=False, default="medium")
    enabled = Column(Boolean, default=True)
