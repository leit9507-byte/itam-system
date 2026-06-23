from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class AssetAttachment(Base):
    __tablename__ = "asset_attachments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    storage_path = Column(String(512), nullable=False)
    size = Column(Integer, default=0, nullable=False)
    uploaded_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
