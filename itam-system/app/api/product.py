from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.asset import Asset
from app.models.product import DeviceType, ProductCatalog
from app.schemas.product import DeviceTypeOut, DeviceTypeUpsert, ProductBatchRetirementYearsUpdate, ProductOut, ProductUpsert
from app.services.audit_log_service import AuditLogService
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/device-types", response_model=list[DeviceTypeOut])
def list_device_types(db: Session = Depends(get_db)):
    ensure_seed(db)
    return db.query(DeviceType).order_by(DeviceType.id.desc()).all()


@router.post("/device-types", response_model=DeviceTypeOut)
def create_device_type(payload: DeviceTypeUpsert, request: Request, db: Session = Depends(get_db)):
    clean_name = normalize_product_name(payload.name)
    if not clean_name:
        raise HTTPException(status_code=422, detail="设备类型名称不能为空")
    existed = db.query(DeviceType).filter(func.lower(func.trim(DeviceType.name)) == clean_name).first()
    if existed:
        raise HTTPException(status_code=409, detail="设备类型已存在")
    item = DeviceType(name=payload.name.strip(), description=payload.description)
    db.add(item)
    AuditLogService.record_operation(
        db, "catalog", "create_device_type", operator_from_request(request),
        "device_type", None, f"创建设备类型 {payload.name}", payload.model_dump(),
    )
    db.commit()
    DashboardService.invalidate()
    db.refresh(item)
    return item


@router.put("/device-types/{type_id}", response_model=DeviceTypeOut)
def update_device_type(type_id: int, payload: DeviceTypeUpsert, request: Request, db: Session = Depends(get_db)):
    item = db.get(DeviceType, type_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    old_name = item.name
    clean_name = normalize_product_name(payload.name)
    if not clean_name:
        raise HTTPException(status_code=422, detail="设备类型名称不能为空")
    duplicate = db.query(DeviceType).filter(
        DeviceType.id != type_id,
        func.lower(func.trim(DeviceType.name)) == clean_name,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="设备类型已存在")
    item.name = payload.name.strip()
    item.description = payload.description
    updated_products = db.query(ProductCatalog).filter(ProductCatalog.device_type == old_name).update({"device_type": item.name})
    updated_assets = db.query(Asset).filter(Asset.category == old_name).update({"category": item.name})
    AuditLogService.record_operation(
        db, "catalog", "update_device_type", operator_from_request(request),
        "device_type", str(type_id), f"更新设备类型 {old_name}",
        {
            "before": {"name": old_name},
            "after": payload.model_dump(),
            "updated_products": updated_products,
            "updated_assets": updated_assets,
        },
    )
    db.commit()
    DashboardService.invalidate()
    db.refresh(item)
    return item


@router.delete("/device-types/{type_id}")
def delete_device_type(type_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(DeviceType, type_id)
    if not item:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    if db.query(ProductCatalog).filter(ProductCatalog.device_type == item.name).first() or db.query(Asset).filter(Asset.category == item.name).first():
        raise HTTPException(status_code=409, detail="设备类型仍被产品或资产使用，不能删除")
    item_name = item.name
    db.delete(item)
    AuditLogService.record_operation(
        db, "catalog", "delete_device_type", operator_from_request(request),
        "device_type", str(type_id), f"删除设备类型 {item_name}",
    )
    db.commit()
    DashboardService.invalidate()
    return {"ok": True}


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    ensure_seed(db)
    return db.query(ProductCatalog).order_by(ProductCatalog.id.desc()).all()


@router.post("/products", response_model=ProductOut)
def create_product(payload: ProductUpsert, request: Request, db: Session = Depends(get_db)):
    ensure_product_name_unique(db, payload.product_name)
    data = payload.model_dump()
    data["product_name"] = payload.product_name.strip()
    item = ProductCatalog(**data)
    db.add(item)
    AuditLogService.record_operation(
        db, "catalog", "create_product", operator_from_request(request),
        "product_catalog", None, f"创建产品 {payload.product_name}", payload.model_dump(),
    )
    db.commit()
    DashboardService.invalidate()
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
    DashboardService.invalidate()
    return {
        "ok": True,
        "updated_products": len(products),
        "updated_assets": len(updated_asset_ids),
        "retirement_years": payload.retirement_years,
    }


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpsert, request: Request, db: Session = Depends(get_db)):
    item = db.get(ProductCatalog, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="产品档案不存在")
    ensure_product_name_unique(db, payload.product_name, product_id)

    old_snapshot = {
        "product_name": item.product_name,
        "device_type": item.device_type,
        "brand": item.brand or "",
        "model": item.model or "",
        "spec": item.spec or "",
        "unit_price": float(item.unit_price or 0),
        "default_warehouse": item.default_warehouse or "",
        "retirement_years": item.retirement_years,
    }
    update_data = payload.model_dump()
    update_data["product_name"] = payload.product_name.strip()
    for key, value in update_data.items():
        setattr(item, key, value)
    operator = operator_from_request(request)
    updated_assets = sync_assets_from_product(db, old_snapshot, item, operator)
    AuditLogService.record_operation(
        db, "catalog", "update_product", operator,
        "product_catalog", str(product_id), f"更新产品 {item.product_name}",
        {"before": old_snapshot, "after": payload.model_dump(), "updated_assets": updated_assets},
    )
    db.commit()
    DashboardService.invalidate()
    db.refresh(item)
    return item


@router.delete("/products/{product_id}")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(ProductCatalog, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="产品档案不存在")
    item_name = item.product_name
    db.delete(item)
    AuditLogService.record_operation(
        db, "catalog", "delete_product", operator_from_request(request),
        "product_catalog", str(product_id), f"删除产品 {item_name}",
    )
    db.commit()
    DashboardService.invalidate()
    return {"ok": True}


def sync_assets_from_product(db: Session, old_snapshot: dict, product: ProductCatalog, operator: str = "system") -> int:
    assets = (
        db.query(Asset)
        .filter(
            func.lower(func.trim(Asset.name)) == normalize_product_name(old_snapshot["product_name"]),
        )
        .all()
    )
    for asset in assets:
        previous = {
            "name": asset.name,
            "category": asset.category,
            "brand": asset.brand,
            "model": asset.model,
            "spec": (asset.config or {}).get("spec"),
            "retirement_years": (asset.config or {}).get("retirement_years"),
        }
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
        if product.default_warehouse and not asset.location:
            asset.location = product.default_warehouse
        current = {
            "name": asset.name,
            "category": asset.category,
            "brand": asset.brand,
            "model": asset.model,
            "spec": config.get("spec"),
            "retirement_years": config.get("retirement_years"),
        }
        for field_name, field_label in {
            "name": "产品名称",
            "category": "设备类型",
            "brand": "品牌",
            "model": "型号",
            "spec": "规格",
            "retirement_years": "退役年限",
        }.items():
            AuditLogService.record_asset_change(
                db,
                asset.asset_id,
                field_name,
                previous[field_name],
                current[field_name],
                operator,
                field_label,
                "product_update",
            )
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


def normalize_product_name(value: str | None) -> str:
    return (value or "").strip().lower()


def ensure_product_name_unique(db: Session, product_name: str, current_product_id: int | None = None) -> None:
    clean_name = normalize_product_name(product_name)
    if not clean_name:
        raise HTTPException(status_code=422, detail="产品名称不能为空")
    query = db.query(ProductCatalog).filter(func.lower(func.trim(ProductCatalog.product_name)) == clean_name)
    if current_product_id is not None:
        query = query.filter(ProductCatalog.id != current_product_id)
    if query.first():
        raise HTTPException(status_code=409, detail="产品名称已存在")


def ensure_seed(db: Session) -> None:
    return None
