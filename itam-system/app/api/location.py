from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset
from app.models.location import Location
from app.schemas.location import LocationOut, LocationSave


router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/list", response_model=list[LocationOut])
def list_locations(keyword: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Location)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(Location.name.like(pattern))
    rows = query.order_by(Location.id.asc()).all()
    counts = Counter(value for (value,) in db.query(Asset.location).all() if value)
    return [LocationOut.model_validate(row).model_copy(update={"asset_count": counts.get(row.name, 0)}) for row in rows]


@router.post("/save", response_model=LocationOut)
def save_location(payload: LocationSave, db: Session = Depends(get_db)):
    name = normalize_name(payload.name)
    existed = db.query(Location).filter(Location.name == name).first()
    if existed:
        raise HTTPException(status_code=409, detail="location already exists")
    row = Location(
        name=name,
        code=payload.code,
        type=payload.type,
        owner_dept=payload.owner_dept,
        description=payload.description,
        status=payload.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return LocationOut.model_validate(row).model_copy(update={"asset_count": 0})


@router.put("/{location_id}", response_model=LocationOut)
def update_location(location_id: int, payload: LocationSave, db: Session = Depends(get_db)):
    row = db.get(Location, location_id)
    if not row:
        raise HTTPException(status_code=404, detail="location not found")
    name = normalize_name(payload.name)
    duplicated = db.query(Location).filter(Location.name == name, Location.id != location_id).first()
    if duplicated:
        raise HTTPException(status_code=409, detail="location already exists")
    row.name = name
    row.code = payload.code
    row.type = payload.type
    row.owner_dept = payload.owner_dept
    row.description = payload.description
    row.status = payload.status
    db.commit()
    db.refresh(row)
    asset_count = db.query(Asset).filter(Asset.location == row.name).count()
    return LocationOut.model_validate(row).model_copy(update={"asset_count": asset_count})


@router.delete("/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)):
    row = db.get(Location, location_id)
    if not row:
        raise HTTPException(status_code=404, detail="location not found")
    if db.query(Asset).filter(Asset.location == row.name).count():
        raise HTTPException(status_code=400, detail="location is used by assets")
    db.delete(row)
    db.commit()
    return {"ok": True}


def normalize_name(value: str | None) -> str:
    clean = (value or "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="location name is required")
    return clean
