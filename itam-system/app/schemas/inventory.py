from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InventoryItemBase(BaseModel):
    item_type: str
    code: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    spec: Optional[str] = None
    total_qty: int = 0
    available_qty: Optional[int] = None
    min_qty: int = 0
    unit_cost: float = 0
    license_key: Optional[str] = None
    expire_date: Optional[datetime] = None
    supplier: Optional[str] = None
    location: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    item_type: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    spec: Optional[str] = None
    total_qty: Optional[int] = None
    available_qty: Optional[int] = None
    min_qty: Optional[int] = None
    unit_cost: Optional[float] = None
    license_key: Optional[str] = None
    expire_date: Optional[datetime] = None
    supplier: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class InventoryItemOut(InventoryItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    available_qty: int
    assigned_qty: int
    created_at: datetime
    updated_at: datetime


class InventoryLedgerCreate(BaseModel):
    action: str
    quantity: int = 1
    assignee_user_id: Optional[str] = None
    assignee_name: Optional[str] = None
    dept_id: Optional[str] = None
    asset_id: Optional[str] = None
    location: Optional[str] = None
    remark: Optional[str] = None


class InventoryLedgerOut(InventoryLedgerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    operator: str
    created_at: datetime
