from app.core.time import TimezoneModel

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field


class InventoryItemBase(TimezoneModel):
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
    dept_id: Optional[str] = None
    location: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(TimezoneModel):
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
    dept_id: Optional[str] = None
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


class InventoryLedgerCreate(TimezoneModel):
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


class LicenseSeatBatchCreate(TimezoneModel):
    count: int = Field(default=1, ge=1, le=1000)
    seat_codes: list[str] = Field(default_factory=list)
    remark: Optional[str] = None


class LicenseSeatAssign(TimezoneModel):
    assignee_user_id: Optional[str] = None
    assignee_name: Optional[str] = None
    dept_id: Optional[str] = None
    asset_id: Optional[str] = None
    remark: Optional[str] = None


class LicenseSeatReturn(TimezoneModel):
    remark: Optional[str] = None


class LicenseSeatOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    seat_code: str
    status: str
    assignee_user_id: Optional[str] = None
    assignee_name: Optional[str] = None
    dept_id: Optional[str] = None
    asset_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LicenseSeatHistoryOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seat_id: int
    action: str
    assignee_user_id: Optional[str] = None
    assignee_name: Optional[str] = None
    dept_id: Optional[str] = None
    asset_id: Optional[str] = None
    operator: str
    remark: Optional[str] = None
    created_at: datetime


class LicenseSeatPage(TimezoneModel):
    list: list[LicenseSeatOut]
    total: int
    page: int
    page_size: int
    summary: dict[str, int]


class ComponentInstallationOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    asset_id: str
    asset_name: Optional[str] = None
    quantity: int
    dept_id: Optional[str] = None
    installed_by: str
    installed_at: datetime
    remark: Optional[str] = None
    updated_at: datetime


class ComponentInstallationPage(TimezoneModel):
    list: list[ComponentInstallationOut]
    total: int
    page: int
    page_size: int
