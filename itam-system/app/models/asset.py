from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String

from app.core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    sn = Column(String(128), unique=True, nullable=True, index=True)
    config = Column(JSON, nullable=True)
    purchase_price = Column(Float, default=0)
    status = Column(String(32), default="in_stock", index=True)
    owner_user_id = Column(String(64), nullable=True, index=True)
    dept_id = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
