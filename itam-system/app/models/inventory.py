from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_type = Column(String(32), nullable=False, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    spec = Column(String(255), nullable=True)
    total_qty = Column(Integer, default=0, nullable=False)
    available_qty = Column(Integer, default=0, nullable=False)
    assigned_qty = Column(Integer, default=0, nullable=False)
    min_qty = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0, nullable=False)
    license_key = Column(String(255), nullable=True)
    expire_date = Column(DateTime, nullable=True)
    supplier = Column(String(128), nullable=True)
    location = Column(String(128), nullable=True)
    status = Column(String(32), default="active", nullable=False, index=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    assignee_user_id = Column(String(64), nullable=True, index=True)
    assignee_name = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=True, index=True)
    location = Column(String(128), nullable=True)
    operator = Column(String(64), nullable=False, default="system")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
