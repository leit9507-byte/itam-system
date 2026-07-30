from app.core.time import TimezoneModel

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field


class UserUpsert(TimezoneModel):
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
    asset_assignment_required: bool | None = None


class UserOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: str
    email: str | None
    dept_id: str | None
    dept_name: str | None
    role: str
    source: str
    identity_provider_id: int | None = None
    status: str
    external_id: str | None
    last_synced_at: datetime | None
    created_at: datetime
    failed_login_count: int = 0
    locked_until: datetime | None = None
    asset_assignment_required: bool = True
    last_login_at: datetime | None = None


class UserAssetAssignmentUpdate(TimezoneModel):
    asset_assignment_required: bool = True


class IdentityProviderSave(TimezoneModel):
    name: str
    provider_type: str = Field(pattern="^ldap$")
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class IdentityProviderOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    enabled: bool
    config: dict[str, Any] | None
    last_test_status: str | None
    last_test_message: str | None
    updated_at: datetime


class LoginRequest(TimezoneModel):
    username: str
    password: str = ""
    provider: str = "local"
    remember_me: bool = False


class LoginResponse(TimezoneModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RolePermissionSave(TimezoneModel):
    role: str
    resource: str
    action: str
    allowed: bool = True


class UserPermissionUpdate(TimezoneModel):
    role: str
    status: str = "active"


class RolePermissionOut(TimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    resource: str
    action: str
    allowed: bool


class SyncUsersRequest(TimezoneModel):
    provider_id: int | None = None
    users: list[UserUpsert] = Field(default_factory=list)


class SyncUsersResponse(TimezoneModel):
    created: int
    updated: int
    offboarded: int = 0
    users: list[UserOut]
