from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import Asset
from app.models.product import DeviceType, ProductCatalog
from app.schemas.product import DeviceTypeOut, DeviceTypeUpsert, ProductOut, ProductUpsert


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
        asset.name = product.product_name
        asset.category = product.device_type
        asset.brand = product.brand
        asset.model = product.model
        asset.config = config
        asset.purchase_price = product.unit_price or asset.purchase_price
        if product.default_warehouse and not asset.location:
            asset.location = product.default_warehouse
    return len(assets)


def nullable_text_match(column, value: str):
    if value:
        return column == value
    return or_(column.is_(None), column == "")


def ensure_seed(db: Session) -> None:
    if db.query(DeviceType).count() == 0:
        db.add_all(
            [
                DeviceType(name="笔记本电脑", description="移动办公电脑"),
                DeviceType(name="显示器", description="显示设备"),
                DeviceType(name="网络设备", description="交换机、路由器、防火墙等"),
                DeviceType(name="打印设备", description="打印机和复合机"),
            ]
        )
    if db.query(ProductCatalog).count() == 0:
        db.add_all(
            [
                ProductCatalog(product_name="ThinkPad X1 Carbon", device_type="笔记本电脑", brand="Lenovo", model="X1 Carbon Gen 12", spec="Ultra 7 / 32GB / 1TB", unit_price=15000, default_warehouse="上海 IT 仓"),
                ProductCatalog(product_name="MacBook Pro 14", device_type="笔记本电脑", brand="Apple", model="M3 Pro", spec="18GB / 512GB", unit_price=17000, default_warehouse="上海 IT 仓"),
                ProductCatalog(product_name="Dell U2723QE", device_type="显示器", brand="Dell", model="U2723QE", spec="27寸 4K", unit_price=3999, default_warehouse="上海 IT 仓"),
            ]
        )
    db.commit()
