from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class AuditReportArchive(Base):
    __tablename__ = "audit_report_archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_no = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    report_type = Column(String(32), nullable=False, default="audit")
    status = Column(String(32), nullable=False, default="generated")
    total_assets = Column(Integer, nullable=False, default=0)
    risk_score = Column(Integer, nullable=False, default=0)
    violation_count = Column(Integer, nullable=False, default=0)
    html_path = Column(String(512), nullable=False)
    pdf_path = Column(String(512), nullable=True)
    xlsx_path = Column(String(512), nullable=True)
    created_by = Column(String(128), nullable=True)
    scope_key = Column(String(160), nullable=False, default="global", index=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)
