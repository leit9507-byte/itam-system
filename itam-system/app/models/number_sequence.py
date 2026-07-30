from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    key = Column(String(64), primary_key=True)
    current_value = Column(Integer, nullable=False, default=0)
    updated_at = Column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)
