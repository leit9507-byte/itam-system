from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import user_context_from_request
from app.services.todo_service import TodoService


router = APIRouter(prefix="/todo", tags=["Todo"])


@router.get("/list")
def list_todos(request: Request, db: Session = Depends(get_db)):
    # 待办计算的唯一实现位于 TodoService（含 45s 缓存）；此处只做转发。
    return TodoService.list_todos(db, user_context_from_request(request))
