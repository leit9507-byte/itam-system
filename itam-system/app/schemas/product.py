from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeviceTypeUpsert(BaseModel):
    name: str
    description: Optional[str] = None


class DeviceTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class ProductUpsert(BaseModel):
    product_name: str
    device_type: str
    brand: Optional[str] = None
    model: Optional[str] = None
    spec: Optional[str] = None
    unit_price: float = 0
    default_warehouse: Optional[str] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    device_type: str
    brand: Optional[str]
    model: Optional[str]
    spec: Optional[str]
    unit_price: float
    default_warehouse: Optional[str]
    created_at: datetime
