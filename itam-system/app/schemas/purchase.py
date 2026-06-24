from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PurchaseItemCreate(BaseModel):
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=0, ge=0)
    location: Optional[str] = None
    dept_id: Optional[str] = None


class PurchaseCreate(BaseModel):
    purchase_no: str
    supplier_name: Optional[str] = None
    total_amount: float = Field(default=0, ge=0)
    status: str = "created"
    items: List[PurchaseItemCreate] = Field(default_factory=list)


class PurchaseReceive(BaseModel):
    operator: str = "system"


class AcceptedAssetCreate(BaseModel):
    sn: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    spec: Optional[str] = None
    location: Optional[str] = None
    dept_id: Optional[str] = None
    owner_user_id: Optional[str] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[datetime] = None
    purchase_approval_no: Optional[str] = None
    purchase_supplier_name: Optional[str] = None
    warranty_expire_date: Optional[datetime] = None
    warranty_months: Optional[int] = None


class PurchaseItemAcceptance(BaseModel):
    item_id: int
    assets: List[AcceptedAssetCreate] = Field(default_factory=list)


class PurchaseAcceptanceReceive(BaseModel):
    operator: str = "system"
    acceptances: List[PurchaseItemAcceptance] = Field(default_factory=list)


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    quantity: int
    unit_price: float
    location: Optional[str]
    dept_id: Optional[str]

class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_no: str
    supplier_name: Optional[str] = None
    total_amount: float
    status: str
    items: List[PurchaseItemOut] = Field(default_factory=list)
