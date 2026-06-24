from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RepairCreate(BaseModel):
    asset_id: str
    repair_time: datetime
    fault_reason: str
    repair_cost: float = Field(default=0, ge=0)
    vendor: Optional[str] = None
    operator: str = "资产管理员"
    remark: Optional[str] = None


class RepairFinish(BaseModel):
    finish_time: Optional[datetime] = None
    next_status: str = "in_stock"
    operator: str = "资产管理员"
    remark: Optional[str] = None


class RepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_no: str
    asset_id: str
    repair_time: datetime
    fault_reason: str
    repair_cost: float
    vendor: Optional[str]
    operator: str
    status: str
    finish_time: Optional[datetime]
    remark: Optional[str]
    created_at: datetime
    asset_name: Optional[str] = None
    sn: Optional[str] = None
    category: Optional[str] = None
    owner: Optional[str] = None
    dept: Optional[str] = None
    current_status: Optional[str] = None
