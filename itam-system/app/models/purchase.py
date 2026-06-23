from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_no = Column(String(64), unique=True, nullable=False, index=True)
    total_amount = Column(Float, default=0)
    status = Column(String(32), default="created", index=True)

    items = relationship("PurchaseItem", cascade="all, delete-orphan", back_populates="purchase")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    location = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True)

    purchase = relationship("Purchase", back_populates="items")
