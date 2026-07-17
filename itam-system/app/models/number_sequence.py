from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    key = Column(String(64), primary_key=True)
    current_value = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
