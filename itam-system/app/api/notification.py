from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.notification import NotificationSettingOut, NotificationSettingSave, NotificationTestRequest
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notification", tags=["Notification"])


@router.get("/settings", response_model=NotificationSettingOut)
def get_notification_setting(db: Session = Depends(get_db)):
    return NotificationService.get_setting(db)


@router.get("/previews")
def get_notification_previews():
    return NotificationService.preview_messages()


@router.post("/settings", response_model=NotificationSettingOut)
def save_notification_setting(payload: NotificationSettingSave, db: Session = Depends(get_db)):
    try:
        return NotificationService.save_setting(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/test", response_model=NotificationSettingOut)
def test_notification(payload: NotificationTestRequest, db: Session = Depends(get_db)):
    try:
        return NotificationService.send_test(db, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
