from sqlalchemy import JSON, Column, Integer, Numeric, String, Text

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String(64), primary_key=True, index=True)
    asset_no = Column(String(64), unique=True, nullable=False, index=True)
    company = Column(String(128), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    brand = Column(String(64), nullable=True)
    model = Column(String(64), nullable=True)
    sn = Column(String(128), unique=True, nullable=True, index=True)
    config = Column(JSON, nullable=True)
    purchase_price = Column(Numeric(12, 2, asdecimal=False), default=0)
    purchase_date = Column(UTCDateTime, nullable=True)
    purchase_approval_no = Column(String(128), nullable=True, index=True)
    purchase_supplier_name = Column(String(128), nullable=True, index=True)
    warranty_expire_date = Column(UTCDateTime, nullable=True)
    warranty_months = Column(Integer, nullable=True)
    status = Column(String(32), default="in_stock", index=True)
    owner_user_id = Column(String(64), nullable=True, index=True)
    dept_id = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True, index=True)
    remark = Column(Text, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False, index=True)

    @property
    def current_residual_value(self) -> float:
        from app.services.asset_residual_service import AssetResidualService

        return AssetResidualService.calculate_asset(self)
