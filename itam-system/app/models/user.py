from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String

from app.core.database import Base
from app.core.time import UTCDateTime, utc_now


class UserDirectory(Base):
    __tablename__ = "user_directory"

    user_id = Column(String(64), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True, index=True)
    dept_id = Column(String(64), nullable=True, index=True)
    dept_name = Column(String(128), nullable=True)
    role = Column(String(32), default="user", nullable=False)
    source = Column(String(32), default="local", nullable=False, index=True)
    identity_provider_id = Column(Integer, ForeignKey("identity_provider_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(32), default="active", nullable=False)
    password_hash = Column(String(255), nullable=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(UTCDateTime, nullable=True)
    asset_assignment_required = Column(Boolean, default=True, nullable=False)
    external_id = Column(String(128), nullable=True, index=True)
    last_login_at = Column(UTCDateTime, nullable=True)
    last_synced_at = Column(UTCDateTime, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)


class IdentityProviderConfig(Base):
    __tablename__ = "identity_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    provider_type = Column(String(32), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    config = Column(JSON, nullable=True)
    last_test_status = Column(String(32), nullable=True)
    last_test_message = Column(String(255), nullable=True)
    updated_at = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(32), nullable=False, index=True)
    resource = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)
    allowed = Column(Boolean, default=True, nullable=False)
