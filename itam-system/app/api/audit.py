from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.reports.generator import AuditReportGenerator
from app.services.audit_engine import AuditEngine


router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditRunRequest(BaseModel):
    users: list[dict] = []


last_report_path: str | None = None


@router.post("/run")
def run_audit(payload: AuditRunRequest | None = None, db: Session = Depends(get_db)):
    global last_report_path
    result = AuditEngine(db).run(users=payload.users if payload else [])
    last_report_path = AuditReportGenerator().generate(result)
    return result


@router.get("/report")
def get_audit_report(db: Session = Depends(get_db)):
    global last_report_path
    if not last_report_path:
        result = AuditEngine(db).run()
        last_report_path = AuditReportGenerator().generate(result)
    return FileResponse(last_report_path, media_type="text/html", filename="audit_report.html")
