from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import user_context_from_request
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/enterprise")
def enterprise_dashboard(
    request: Request,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
):
    date_range = [date_from, date_to] if date_from and date_to else None
    return DashboardService.enterprise(db, user_context_from_request(request), date_range)
