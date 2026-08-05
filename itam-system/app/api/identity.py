from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import decode_access_token
from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.user import RolePermission, UserDirectory
from app.schemas.user import (
    IdentityProviderOut,
    IdentityProviderSave,
    LoginRequest,
    LoginResponse,
    RolePermissionSave,
    RolePermissionOut,
    SyncUsersRequest,
    SyncUsersResponse,
    UserAssetAssignmentUpdate,
    UserPermissionUpdate,
    UserOut,
    UserUpsert,
)
from app.services.identity_service import IdentityService
from app.services.audit_log_service import AuditLogService
from app.services.todo_service import TodoService


router = APIRouter(tags=["Identity"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return IdentityService.authenticate(db, payload.username, payload.password, payload.provider, payload.remember_me)
    except PermissionError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/auth/me/permissions")
def current_permissions(request: Request, db: Session = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(UserDirectory, payload["sub"])
    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="User disabled or not found")
    if user.role == "admin":
        return {
            "role": user.role,
            "resources": ["asset", "purchase", "repair", "supplier", "catalog", "audit", "identity", "rbac", "file", "report", "ops"],
            "permissions": [],
        }
    rows = (
        db.query(RolePermission)
        .filter(RolePermission.role == user.role, RolePermission.allowed.is_(True), RolePermission.action.in_(["read", "*"]))
        .all()
    )
    resources = sorted({row.resource for row in rows})
    return {
        "role": user.role,
        "resources": resources,
        "permissions": [{"resource": row.resource, "action": row.action, "allowed": row.allowed} for row in rows],
    }


@router.get("/users/list", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return IdentityService.list_users(db)


@router.post("/users/save", response_model=UserOut)
def save_user(payload: UserUpsert, request: Request, db: Session = Depends(get_db)):
    try:
        row = IdentityService.save_local_user(db, payload)
        AuditLogService.record_operation(db, "identity", "save_user", operator_from_request(request), "user", row.user_id, f"保存用户 {row.user_id}")
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        user = IdentityService.delete_local_user(db, user_id)
        AuditLogService.record_operation(db, "identity", "delete_user", operator_from_request(request), "user", user_id, f"删除/离职用户 {user_id}")
        db.commit()
        return {"message": "user marked resigned", "user": user}
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "user not found" else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.put("/users/{user_id}/permissions", response_model=UserOut)
def update_user_permissions(user_id: str, payload: UserPermissionUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        row = IdentityService.update_user_permissions(db, user_id, payload)
        AuditLogService.record_operation(db, "identity", "update_user_permissions", operator_from_request(request), "user", user_id, f"更新用户权限 {user_id}", payload.model_dump())
        db.commit()
        return row
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "user not found" else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.put("/users/{user_id}/asset-assignment", response_model=UserOut)
def update_user_asset_assignment(user_id: str, payload: UserAssetAssignmentUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        row = IdentityService.update_asset_assignment_required(db, user_id, payload.asset_assignment_required)
        AuditLogService.record_operation(
            db,
            "identity",
            "update_user_asset_assignment",
            operator_from_request(request),
            "user",
            user_id,
            f"更新用户资产分配要求 {user_id}",
            payload.model_dump(),
        )
        TodoService.invalidate()
        db.commit()
        return row
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "user not found" else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/users/sync", response_model=SyncUsersResponse)
def sync_users(payload: SyncUsersRequest, request: Request, db: Session = Depends(get_db)):
    try:
        created, updated, offboarded, users = IdentityService.sync_users(db, payload.provider_id, payload.users)
        AuditLogService.record_operation(
            db,
            "identity",
            "sync_users",
            operator_from_request(request),
            "user_directory",
            "batch",
            f"同步用户：新增 {created}，更新 {updated}，离职 {offboarded}",
            {"provider_id": payload.provider_id, "submitted_users": len(payload.users or [])},
        )
        db.commit()
        return {"created": created, "updated": updated, "offboarded": offboarded, "users": users}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/identity/providers", response_model=list[IdentityProviderOut])
def list_providers(db: Session = Depends(get_db)):
    return IdentityService.list_providers(db)


@router.get("/rbac/permissions", response_model=list[RolePermissionOut])
def list_permissions(db: Session = Depends(get_db)):
    return IdentityService.list_permissions(db)


@router.post("/rbac/permissions", response_model=list[RolePermissionOut])
def save_permissions(payload: list[RolePermissionSave], request: Request, db: Session = Depends(get_db)):
    try:
        rows = IdentityService.save_permissions(db, payload)
        AuditLogService.record_operation(db, "rbac", "save_permissions", operator_from_request(request), "role_permission", "batch", "保存角色权限", [item.model_dump() for item in payload])
        db.commit()
        return rows
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/identity/providers", response_model=IdentityProviderOut)
def create_provider(payload: IdentityProviderSave, request: Request, db: Session = Depends(get_db)):
    row = IdentityService.save_provider(db, payload)
    AuditLogService.record_operation(db, "identity", "create_provider", operator_from_request(request), "identity_provider", str(row.id), f"创建身份源 {row.name}")
    db.commit()
    return row


@router.put("/identity/providers/{provider_id}", response_model=IdentityProviderOut)
def update_provider(provider_id: int, payload: IdentityProviderSave, request: Request, db: Session = Depends(get_db)):
    try:
        row = IdentityService.save_provider(db, payload, provider_id)
        AuditLogService.record_operation(db, "identity", "update_provider", operator_from_request(request), "identity_provider", str(provider_id), f"更新身份源 {row.name}")
        db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/identity/providers/{provider_id}")
def delete_provider(provider_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        IdentityService.delete_provider(db, provider_id)
        AuditLogService.record_operation(db, "identity", "delete_provider", operator_from_request(request), "identity_provider", str(provider_id), f"删除身份源 {provider_id}")
        db.commit()
        return {"message": "identity provider deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/identity/providers/{provider_id}/test", response_model=IdentityProviderOut)
def test_provider(provider_id: int, db: Session = Depends(get_db)):
    try:
        return IdentityService.test_provider(db, provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
