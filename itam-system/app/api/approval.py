from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.approval import ApprovalRule


router = APIRouter(prefix="/approval", tags=["Approval"])


class ApprovalRulePayload(BaseModel):
    flow_type: str
    name: str
    enabled: bool = True
    min_amount: float | None = None
    max_amount: float | None = None
    dept_id: str | None = None
    approver_role: str | None = None
    approver_user_id: str | None = None
    level: int = 1
    require_all: bool = False


def rule_out(row: ApprovalRule) -> dict:
    return {
        "id": row.id,
        "flow_type": row.flow_type,
        "name": row.name,
        "enabled": row.enabled,
        "min_amount": row.min_amount,
        "max_amount": row.max_amount,
        "dept_id": row.dept_id,
        "approver_role": row.approver_role,
        "approver_user_id": row.approver_user_id,
        "level": row.level,
        "require_all": row.require_all,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/rules")
def list_rules(flow_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRule)
    if flow_type:
        query = query.filter(ApprovalRule.flow_type == flow_type)
    rows = query.order_by(ApprovalRule.flow_type.asc(), ApprovalRule.level.asc(), ApprovalRule.id.asc()).all()
    return [rule_out(row) for row in rows]


@router.post("/rules")
def create_rule(payload: ApprovalRulePayload, db: Session = Depends(get_db)):
    row = ApprovalRule(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return rule_out(row)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, payload: ApprovalRulePayload, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval rule not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return rule_out(row)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    row = db.get(ApprovalRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="approval rule not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/evaluate")
def evaluate_rules(flow_type: str, amount: float = 0, dept_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ApprovalRule).filter(ApprovalRule.enabled.is_(True), ApprovalRule.flow_type == flow_type)
    query = query.filter(or_(ApprovalRule.min_amount.is_(None), ApprovalRule.min_amount <= amount))
    query = query.filter(or_(ApprovalRule.max_amount.is_(None), ApprovalRule.max_amount >= amount))
    if dept_id:
        query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == "", ApprovalRule.dept_id == dept_id))
    else:
        query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == ""))
    rows = query.order_by(ApprovalRule.level.asc(), ApprovalRule.id.asc()).all()
    return {"flow_type": flow_type, "amount": amount, "dept_id": dept_id, "levels": [rule_out(row) for row in rows]}
