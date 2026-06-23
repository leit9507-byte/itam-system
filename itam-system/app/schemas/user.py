from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserUpsert(BaseModel):
    user_id: str | None = None
    username: str
    display_name: str
    email: str | None = None
    dept_id: str | None = None
    dept_name: str | None = None
    role: str = "user"
    source: str = "local"
    status: str = "active"
    external_id: str | None = None
    password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: str
    email: str | None
    dept_id: str | None
    dept_name: str | None
    role: str
    source: str
    status: str
    external_id: str | None
    last_synced_at: datetime | None
    created_at: datetime
    failed_login_count: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None


class IdentityProviderSave(BaseModel):
    name: str
    provider_type: str = Field(pattern="^(ldap|oidc|saml|feishu|wechat_work|local)$")
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class IdentityProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    enabled: bool
    config: dict[str, Any] | None
    last_test_status: str | None
    last_test_message: str | None
    updated_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str = ""
    provider: str = "local"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RolePermissionSave(BaseModel):
    role: str
    resource: str
    action: str
    allowed: bool = True


class RolePermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    resource: str
    action: str
    allowed: bool


class SyncUsersRequest(BaseModel):
    provider_id: int | None = None
    users: list[UserUpsert] = Field(default_factory=list)


class SyncUsersResponse(BaseModel):
    created: int
    updated: int
    users: list[UserOut]
