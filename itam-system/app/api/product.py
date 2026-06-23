from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    item.name = payload.name
    item.description = payload.description
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
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def ensure_seed(db: Session) -> None:
    if db.query(DeviceType).count() == 0:
        db.add_all(
            [
                DeviceType(name="Laptop", description="笔记本电脑"),
                DeviceType(name="Monitor", description="显示器"),
                DeviceType(name="Network", description="网络设备"),
                DeviceType(name="Printer", description="打印设备"),
            ]
        )
    if db.query(ProductCatalog).count() == 0:
        db.add_all(
            [
                ProductCatalog(product_name="ThinkPad X1 Carbon", device_type="Laptop", brand="Lenovo", model="X1 Carbon Gen 12", spec="Ultra 7 / 32GB / 1TB", unit_price=15000, default_warehouse="上海 IT 库"),
                ProductCatalog(product_name="MacBook Pro 14", device_type="Laptop", brand="Apple", model="M3 Pro", spec="18GB / 512GB", unit_price=17000, default_warehouse="上海 IT 库"),
                ProductCatalog(product_name="Dell U2723QE", device_type="Monitor", brand="Dell", model="U2723QE", spec="27寸 4K", unit_price=3999, default_warehouse="上海 IT 库"),
            ]
        )
    db.commit()
