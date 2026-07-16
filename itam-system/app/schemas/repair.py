from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RepairCreate(BaseModel):
    asset_id: str
    repair_time: datetime
    repair_type: str = "普通维修"
    fault_reason: str
    repair_cost: float = Field(default=0, ge=0)
    vendor: Optional[str] = None
    operator: str = "资产管理员"
    remark: Optional[str] = None


class RepairFinish(BaseModel):
    finish_time: Optional[datetime] = None
    next_status: str = "in_stock"
    repair_result: str = "已修好"
    operator: str = "资产管理员"
    remark: Optional[str] = None


class RepairFaultTypeSave(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: str = "启用"


class RepairFaultTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    enabled: str
    created_at: datetime


class RepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_no: str
    asset_id: str
    repair_time: datetime
    repair_type: str = "普通维修"
    fault_reason: str
    repair_cost: float
    vendor: Optional[str]
    operator: str
    status: str
    repair_result: Optional[str] = None
    finish_time: Optional[datetime]
    remark: Optional[str]
    created_at: datetime
    asset_name: Optional[str] = None
    sn: Optional[str] = None
    category: Optional[str] = None
    asset_model: Optional[str] = None
    owner: Optional[str] = None
    dept: Optional[str] = None
    current_status: Optional[str] = None
