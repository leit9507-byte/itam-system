from collections import Counter, defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset
from app.models.company import Company


router = APIRouter(prefix="/company", tags=["Company"])
DEFAULT_COMPANY = "未设置公司"


class CompanySave(BaseModel):
    name: str
    code: str | None = None
    contact: str | None = None
    status: str = "启用"


def normalize_company(value: str | None) -> str:
    clean = (value or "").strip()
    return clean or DEFAULT_COMPANY


def stored_company(value: str | None) -> str | None:
    clean = (value or "").strip()
    return None if not clean or clean == DEFAULT_COMPANY else clean


ASSET_STATUS_LABELS = {
    "pending_purchase": "待采购",
    "pending_acceptance": "待验收",
    "in_stock": "在库",
    "in_use": "在用",
    "idle": "闲置",
    "borrowed": "借出",
    "repair": "维修中",
    "out_stock": "已出库",
    "pending_scrap": "待报废",
    "scrapped": "已报废",
}


@router.get("/list")
def list_companies(db: Session = Depends(get_db)):
    ensure_company_data(db)
    companies = db.query(Company).order_by(Company.id.asc()).all()
    assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
    groups = defaultdict(list)
    for asset in assets:
        groups[normalize_company(asset.company)].append(asset)

    rows = []
    for company in companies:
        items = groups.get(company.name, [])
        status_counter = Counter(asset.status or "unknown" for asset in items)
        rows.append(
            {
                "id": company.id,
                "name": company.name,
                "code": company.code,
                "contact": company.contact,
                "status": company.status,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "asset_count": len(items),
                "total_original_value": sum(asset.purchase_price or 0 for asset in items),
                "in_use_count": status_counter.get("in_use", 0),
                "in_stock_count": status_counter.get("in_stock", 0),
                "idle_count": status_counter.get("idle", 0),
                "repair_count": status_counter.get("repair", 0),
                "scrapped_count": status_counter.get("scrapped", 0),
                "pending_scrap_count": status_counter.get("pending_scrap", 0),
                "status_distribution": [{"name": status_label(key), "value": value} for key, value in status_counter.items()],
                "assets": [asset_row(asset) for asset in items],
            }
        )
    unset_items = groups.get(DEFAULT_COMPANY, [])
    if unset_items:
        status_counter = Counter(asset.status or "unknown" for asset in unset_items)
        rows.append(
            {
                "id": None,
                "name": DEFAULT_COMPANY,
                "code": "",
                "contact": "",
                "status": "未建档",
                "virtual": True,
                "created_at": None,
                "updated_at": None,
                "asset_count": len(unset_items),
                "total_original_value": sum(asset.purchase_price or 0 for asset in unset_items),
                "in_use_count": status_counter.get("in_use", 0),
                "in_stock_count": status_counter.get("in_stock", 0),
                "idle_count": status_counter.get("idle", 0),
                "repair_count": status_counter.get("repair", 0),
                "scrapped_count": status_counter.get("scrapped", 0),
                "pending_scrap_count": status_counter.get("pending_scrap", 0),
                "status_distribution": [{"name": status_label(key), "value": value} for key, value in status_counter.items()],
                "assets": [asset_row(asset) for asset in unset_items],
            }
        )
    return sorted(rows, key=lambda item: item["asset_count"], reverse=True)


@router.post("/save")
def save_company(payload: CompanySave, db: Session = Depends(get_db)):
    name = normalize_company(payload.name)
    if name == DEFAULT_COMPANY:
        raise HTTPException(status_code=400, detail="default company is only a display group")
    existed = db.query(Company).filter(Company.name == name).first()
    if existed:
        raise HTTPException(status_code=409, detail="company already exists")
    company = Company(name=name, code=payload.code, contact=payload.contact, status=payload.status)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.put("/{company_id}")
def update_company(company_id: int, payload: CompanySave, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    old_name = company.name
    new_name = normalize_company(payload.name)
    if new_name == DEFAULT_COMPANY:
        raise HTTPException(status_code=400, detail="default company is only a display group")
    duplicated = db.query(Company).filter(Company.name == new_name, Company.id != company_id).first()
    if duplicated:
        raise HTTPException(status_code=409, detail="company already exists")
    company.name = new_name
    company.code = payload.code
    company.contact = payload.contact
    company.status = payload.status
    company.updated_at = datetime.utcnow()
    db.query(Asset).filter(Asset.company == old_name).update({"company": new_name})
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    old_name = company.name
    db.query(Asset).filter(Asset.company == old_name).update({"company": None})
    db.delete(company)
    db.commit()
    return {"deleted": True, "asset_company_reset": old_name}


def ensure_company_data(db: Session) -> None:
    changed = False
    assets = db.query(Asset).all()
    for asset in assets:
        normalized = stored_company(asset.company)
        if asset.company != normalized:
            asset.company = normalized
            changed = True
    names = {asset.company for asset in assets if stored_company(asset.company)}
    for name in names:
        if not db.query(Company).filter(Company.name == name).first():
            db.add(Company(name=name, status="启用"))
            changed = True
    default_company = db.query(Company).filter(Company.name == DEFAULT_COMPANY).first()
    if default_company:
        db.delete(default_company)
        changed = True
    if changed:
        db.commit()


def asset_row(asset: Asset) -> dict:
    return {
        "asset_id": asset.asset_id,
        "company": normalize_company(asset.company),
        "name": asset.name,
        "category": asset.category,
        "brand": asset.brand,
        "model": asset.model,
        "sn": asset.sn,
        "status": asset.status,
        "status_label": status_label(asset.status),
        "owner_user_id": asset.owner_user_id,
        "dept_id": asset.dept_id,
        "location": asset.location,
        "purchase_price": asset.purchase_price or 0,
        "purchase_supplier_name": asset.purchase_supplier_name,
        "created_at": asset.created_at,
    }


def status_label(value: str | None) -> str:
    return ASSET_STATUS_LABELS.get(value or "", value or "未设置")
