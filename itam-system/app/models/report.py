from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
