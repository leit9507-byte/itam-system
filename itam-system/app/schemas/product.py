from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    retirement_years: Optional[int] = None


class ProductBatchRetirementYearsUpdate(BaseModel):
    product_ids: list[int] = Field(min_length=1, max_length=500)
    retirement_years: int = Field(ge=1, le=100)


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
    retirement_years: Optional[int]
    created_at: datetime
