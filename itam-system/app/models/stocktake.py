from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class StocktakeTask(Base):
    __tablename__ = "stocktake_tasks"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    scope = Column(String(32), nullable=False, default="全部")
    target = Column(String(128), nullable=True)
    owner = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="待开始")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("StocktakeItem", back_populates="task", cascade="all, delete-orphan")


class StocktakeItem(Base):
    __tablename__ = "stocktake_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("stocktake_tasks.id"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=True)
    sn = Column(String(128), nullable=True, index=True)
    book_location = Column(String(128), nullable=True)
    book_status = Column(String(64), nullable=True)
    actual_location = Column(String(128), nullable=True)
    result = Column(String(32), nullable=False, default="未盘")
    checker = Column(String(128), nullable=True)
    checked_at = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)

    task = relationship("StocktakeTask", back_populates="items")
