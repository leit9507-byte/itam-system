from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


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
    expire_date = Column(UTCDateTime, nullable=True)
    supplier = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True)
    status = Column(String(32), default="active", nullable=False, index=True)
    remark = Column(Text, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)


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
    created_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)


class InventoryLicenseSeat(Base):
    __tablename__ = "inventory_license_seats"
    __table_args__ = (UniqueConstraint("item_id", "seat_code", name="uq_inventory_license_seat_code"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False, index=True)
    seat_code = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="available", index=True)
    assignee_user_id = Column(String(64), nullable=True, index=True)
    assignee_name = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=True, index=True)
    assigned_at = Column(UTCDateTime, nullable=True)
    returned_at = Column(UTCDateTime, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)


class InventoryLicenseSeatHistory(Base):
    __tablename__ = "inventory_license_seat_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    seat_id = Column(Integer, ForeignKey("inventory_license_seats.id"), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)
    assignee_user_id = Column(String(64), nullable=True, index=True)
    assignee_name = Column(String(128), nullable=True)
    dept_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=True, index=True)
    operator = Column(String(64), nullable=False, default="system")
    remark = Column(Text, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)


class InventoryComponentInstallation(Base):
    __tablename__ = "inventory_component_installations"
    __table_args__ = (UniqueConstraint("item_id", "asset_id", name="uq_inventory_component_asset"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False, index=True)
    asset_id = Column(String(64), ForeignKey("assets.asset_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    dept_id = Column(String(64), nullable=True, index=True)
    installed_by = Column(String(64), nullable=False, default="system")
    installed_at = Column(UTCDateTime, default=utc_now, nullable=False)
    remark = Column(Text, nullable=True)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
