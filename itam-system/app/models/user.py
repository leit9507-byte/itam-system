from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from app.core.database import Base


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
    status = Column(String(32), default="active", nullable=False)
    password_hash = Column(String(255), nullable=True)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    external_id = Column(String(128), nullable=True, index=True)
    last_login_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class IdentityProviderConfig(Base):
    __tablename__ = "identity_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    provider_type = Column(String(32), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    config = Column(JSON, nullable=True)
    last_test_status = Column(String(32), nullable=True)
    last_test_message = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(32), nullable=False, index=True)
    resource = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)
    allowed = Column(Boolean, default=True, nullable=False)
