from sqlalchemy import Column, Integer, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class AssetAttachment(Base):
    __tablename__ = "asset_attachments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    storage_path = Column(String(512), nullable=False)
    size = Column(Integer, default=0, nullable=False)
    uploaded_by = Column(String(64), nullable=True)
    status = Column(String(32), default="active", nullable=False, index=True)
    archived_at = Column(UTCDateTime, nullable=True)
    deleted_at = Column(UTCDateTime, nullable=True)
    remark = Column(String(512), nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)
