from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.services.asset_residual_service import AssetResidualService


router = APIRouter(prefix="/settings", tags=["Settings"])


class CategoryResidualRate(BaseModel):
    category: str
    minimum_residual_rate: float = Field(ge=0, le=1)


class AssetResidualConfigPayload(BaseModel):
    method: str = Field(default="straight_line", pattern="^(straight_line|double_declining|sum_of_years_digits|fixed_rate)$")
    minimum_residual_rate: float = Field(ge=0, le=1)
    missing_basis_policy: str = "original"
    category_rates: list[CategoryResidualRate] = Field(default_factory=list)


@router.get("/asset-residual")
def get_asset_residual_config(db: Session = Depends(get_db)):
    return AssetResidualService.get_config(db)


@router.put("/asset-residual")
def save_asset_residual_config(payload: AssetResidualConfigPayload, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetResidualService.save_config(db, payload.model_dump(), operator_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
