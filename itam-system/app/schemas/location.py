from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LocationSave(BaseModel):
    name: str
    code: str | None = None
    type: str = "办公位置"
    owner_dept: str | None = None
    description: str | None = None
    status: str = "启用"


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None = None
    type: str
    owner_dept: str | None = None
    description: str | None = None
    status: str
    asset_count: int = 0
    created_at: datetime
    updated_at: datetime
