from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    asset_no: Optional[str] = None
    company: Optional[str] = None
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    purchase_price: float = 0
    purchase_date: Optional[datetime] = None
    purchase_approval_no: Optional[str] = None
    purchase_supplier_name: Optional[str] = None
    warranty_expire_date: Optional[datetime] = None
    warranty_months: Optional[int] = None
    status: str = "in_stock"
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    remark: Optional[str] = None


class AssetStatusChange(BaseModel):
    to_status: str
    operator: str = "system"
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    borrow_due_date: Optional[str] = None
    remark: Optional[str] = None


class AssetCheckoutCreate(BaseModel):
    checkout_type: str = "in_use"
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    due_date: Optional[str] = None
    remark: Optional[str] = None


class AssetCheckinCreate(BaseModel):
    location: Optional[str] = None
    remark: Optional[str] = None


class AssetBatchCheckoutCreate(AssetCheckoutCreate):
    asset_ids: list[str]


class AssetBatchCheckinCreate(AssetCheckinCreate):
    asset_ids: list[str]


class AssetBatchRepairCreate(BaseModel):
    asset_ids: list[str]
    repair_time: datetime
    repair_type: str = "普通维修"
    fault_reason: str
    repair_cost: float = Field(default=0, ge=0)
    vendor: Optional[str] = None
    operator: str = "资产管理员"
    remark: Optional[str] = None


class AssetCheckoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: str
    checkout_type: str
    assignee_user_id: Optional[str] = None
    assignee_name: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    checked_out_at: datetime
    checked_out_by: str
    checked_in_at: Optional[datetime] = None
    checked_in_by: Optional[str] = None
    checkin_location: Optional[str] = None
    remark: Optional[str] = None
    checkin_remark: Optional[str] = None


class AssetUpdate(BaseModel):
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    company: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[datetime] = None
    purchase_approval_no: Optional[str] = None
    purchase_supplier_name: Optional[str] = None
    warranty_expire_date: Optional[datetime] = None
    warranty_months: Optional[int] = None
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    remark: Optional[str] = None


class AssetBatchUpdateCreate(BaseModel):
    asset_ids: list[str]
    updates: AssetUpdate


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_id: Optional[int] = None
    asset_id: str
    asset_no: Optional[str] = None
    company: Optional[str] = None
    name: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    sn: Optional[str]
    config: Optional[Dict[str, Any]]
    purchase_price: float
    current_residual_value: float = 0
    purchase_date: Optional[datetime]
    purchase_approval_no: Optional[str]
    purchase_supplier_name: Optional[str]
    warranty_expire_date: Optional[datetime]
    warranty_months: Optional[int]
    status: str
    owner_user_id: Optional[str]
    owner_display_name: Optional[str] = None
    owner_username: Optional[str] = None
    dept_id: Optional[str]
    dept_name: Optional[str] = None
    location: Optional[str]
    remark: Optional[str] = None
    created_at: datetime


class AssetImportRow(AssetCreate):
    asset_id: Optional[str] = None
    company: Optional[str] = None
    product_name: Optional[str] = None
    owner: Optional[str] = None
    dept: Optional[str] = None
    price: Optional[float] = None
    spec: Optional[str] = None
    payment_time: Optional[str] = None
    payment_no: Optional[str] = None
    remark: Optional[str] = None


class AssetBatchImport(BaseModel):
    operator: str = "asset-import"
    overwrite: bool = False
    items: list[AssetImportRow]


class AssetTextImport(BaseModel):
    operator: str = "asset-import"
    overwrite: bool = False
    content: str


class AssetImportError(BaseModel):
    row: int
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class AssetImportResult(BaseModel):
    created: int
    updated: int = 0
    skipped: int
    errors: list[AssetImportError]
    assets: list[AssetOut]
