from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProductCatalog(Base):
    __tablename__ = "product_catalogs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String(128), nullable=False, index=True)
    device_type = Column(String(64), nullable=False, index=True)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    spec = Column(String(255), nullable=True)
    unit_price = Column(Float, default=0)
    default_warehouse = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
