from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SupplierSave(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    level: str = "普通"
    status: str = "启用"


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_no: str
    name: str
    contact: Optional[str]
    phone: Optional[str]
    level: str
    status: str
    created_at: datetime
    updated_at: datetime
    purchase_count: int = 0
    device_count: int = 0
    total_amount: float = 0
    last_purchase_no: str = ""


class SupplierDeviceOut(BaseModel):
    supplier_name: str
    purchase_no: str
    status: str
    product_name: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    quantity: int
    unit_price: float
    total_amount: float
    warehouse: Optional[str]
    dept: Optional[str]
