from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    purchase_price: float = 0
    status: str = "in_stock"
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None


class AssetStatusChange(BaseModel):
    to_status: str
    operator: str = "system"
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None
    remark: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    purchase_price: Optional[float] = None
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    dept_id: Optional[str] = None
    location: Optional[str] = None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    name: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    sn: Optional[str]
    config: Optional[Dict[str, Any]]
    purchase_price: float
    status: str
    owner_user_id: Optional[str]
    dept_id: Optional[str]
    location: Optional[str]
    created_at: datetime


class AssetImportRow(AssetCreate):
    asset_id: Optional[str] = None
    product_name: Optional[str] = None
    owner: Optional[str] = None
    dept: Optional[str] = None
    price: Optional[float] = None
    spec: Optional[str] = None
    warehouse: Optional[str] = None


class AssetBatchImport(BaseModel):
    operator: str = "asset-import"
    items: list[AssetImportRow]


class AssetTextImport(BaseModel):
    operator: str = "asset-import"
    content: str


class AssetImportError(BaseModel):
    row: int
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class AssetImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[AssetImportError]
    assets: list[AssetOut]
