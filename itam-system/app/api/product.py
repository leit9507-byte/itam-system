from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.asset import Asset
from app.models.product import DeviceType, ProductCatalog
from app.schemas.product import DeviceTypeOut, DeviceTypeUpsert, ProductBatchRetirementYearsUpdate, ProductOut, ProductUpsert
from app.services.audit_log_service import AuditLogService


router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/device-types", response_model=list[DeviceTypeOut])
def list_device_types(db: Session = Depends(get_db)):
    ensure_seed(db)
    return db.query(DeviceType).order_by(DeviceType.id.desc()).all()


@router.post("/device-types", response_model=DeviceTypeOut)
def create_device_type(payload: DeviceTypeUpsert, db: Session = Depends(get_db)):
    existed = db.query(DeviceType).filter(DeviceType.name == payload.name).first()
    if existed:
        raise HTTPException(status_code=409, detail="设备类型已存在")
    item = DeviceType(name=payload.name, description=payload.description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/device-types/{type_id}", response_model=DeviceTypeOut)
def update_device_type(type_id: int, payload: DeviceTypeUpsert, db: Session = Depends(get_db)):
    item = db.get(DeviceType, type_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    old_name = item.name
    item.name = payload.name
    item.description = payload.description
    db.query(ProductCatalog).filter(ProductCatalog.device_type == old_name).update({"device_type": payload.name})
    db.query(Asset).filter(Asset.category == old_name).update({"category": payload.name})
    db.commit()
    db.refresh(item)
    return item


@router.delete("/device-types/{type_id}")
def delete_device_type(type_id: int, db: Session = Depends(get_db)):
    item = db.get(DeviceType, type_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    ensure_seed(db)
    return db.query(ProductCatalog).order_by(ProductCatalog.id.desc()).all()


@router.post("/products", response_model=ProductOut)
def create_product(payload: ProductUpsert, db: Session = Depends(get_db)):
    item = ProductCatalog(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/products/batch-retirement-years")
def batch_update_product_retirement_years(
    payload: ProductBatchRetirementYearsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    product_ids = list(dict.fromkeys(payload.product_ids))
    products = db.query(ProductCatalog).filter(ProductCatalog.id.in_(product_ids)).all()
    found_ids = {item.id for item in products}
    missing_ids = [product_id for product_id in product_ids if product_id not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"产品档案不存在：{', '.join(map(str, missing_ids))}")

    operator = operator_from_request(request)
    updated_asset_ids: set[str] = set()
    for product in products:
        product.retirement_years = payload.retirement_years
        updated_asset_ids.update(
            sync_asset_retirement_years(
                db,
                product.product_name,
                payload.retirement_years,
                operator,
            )
        )

    AuditLogService.record_operation(
        db,
        "catalog",
        "batch_update_retirement_years",
        operator,
        "product_catalog",
        "batch",
        f"批量设置 {len(products)} 个产品退役年限为 {payload.retirement_years} 年",
        {
            "product_ids": product_ids,
            "retirement_years": payload.retirement_years,
            "updated_assets": len(updated_asset_ids),
        },
    )
    db.commit()
    return {
        "ok": True,
        "updated_products": len(products),
        "updated_assets": len(updated_asset_ids),
        "retirement_years": payload.retirement_years,
    }


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpsert, db: Session = Depends(get_db)):
    item = db.get(ProductCatalog, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="产品档案不存在")

    old_snapshot = {
        "product_name": item.product_name,
        "device_type": item.device_type,
        "brand": item.brand or "",
        "model": item.model or "",
    }
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    sync_assets_from_product(db, old_snapshot, item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    item = db.get(ProductCatalog, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="产品档案不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


def sync_assets_from_product(db: Session, old_snapshot: dict, product: ProductCatalog) -> int:
    assets = (
        db.query(Asset)
        .filter(
            Asset.name == old_snapshot["product_name"],
            Asset.category == old_snapshot["device_type"],
            nullable_text_match(Asset.brand, old_snapshot["brand"]),
            nullable_text_match(Asset.model, old_snapshot["model"]),
        )
        .all()
    )
    for asset in assets:
        config = dict(asset.config or {})
        config["spec"] = product.spec or ""
        if product.default_warehouse:
            config["warehouse"] = product.default_warehouse
        if product.retirement_years:
            config["retirement_years"] = product.retirement_years
        else:
            config.pop("retirement_years", None)
        asset.name = product.product_name
        asset.category = product.device_type
        asset.brand = product.brand
        asset.model = product.model
        asset.config = config
        asset.purchase_price = product.unit_price or asset.purchase_price
        if product.default_warehouse and not asset.location:
            asset.location = product.default_warehouse
    return len(assets)


def sync_asset_retirement_years(
    db: Session,
    product_name: str,
    retirement_years: int,
    operator: str,
) -> set[str]:
    clean_name = (product_name or "").strip().lower()
    assets = db.query(Asset).filter(func.lower(func.trim(Asset.name)) == clean_name).all()
    for asset in assets:
        config = dict(asset.config or {})
        old_value = config.get("retirement_years")
        config["retirement_years"] = retirement_years
        asset.config = config
        AuditLogService.record_asset_change(
            db,
            asset.asset_id,
            "retirement_years",
            old_value,
            retirement_years,
            operator,
            "退役年限",
            "product_batch_update",
        )
    return {asset.asset_id for asset in assets}


def nullable_text_match(column, value: str):
    if value:
        return column == value
    return or_(column.is_(None), column == "")


def ensure_seed(db: Session) -> None:
    return None
