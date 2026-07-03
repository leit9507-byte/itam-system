from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    IdentityProviderOut,
    IdentityProviderSave,
    LoginRequest,
    LoginResponse,
    RolePermissionSave,
    RolePermissionOut,
    SyncUsersRequest,
    SyncUsersResponse,
    UserPermissionUpdate,
    UserOut,
    UserUpsert,
)
from app.services.identity_service import IdentityService
from app.services.sso_service import SsoService


router = APIRouter(tags=["Identity"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return IdentityService.authenticate(db, payload.username, payload.password, payload.provider)
    except PermissionError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/auth/sso/{provider_type}/start")
def start_sso(provider_type: str, db: Session = Depends(get_db)):
    provider = db_provider_hint(provider_type, db)
    return {
        "provider": provider_type,
        "redirect_url": provider["redirect_url"],
        "message": provider["message"],
    }


@router.get("/auth/callback/{provider_type}", response_model=LoginResponse)
def sso_callback(provider_type: str, code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    try:
        if provider_type == "oidc":
            if not code:
                raise ValueError("OIDC callback requires authorization code")
            return SsoService.oidc_callback_login(db, code, state)
        if provider_type == "saml":
            raise ValueError("SAML callback requires signed assertion validation and is not enabled yet")
        raise ValueError("unsupported provider callback")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def db_provider_hint(provider_type: str, db: Session) -> dict:
    from app.models.user import IdentityProviderConfig

    row = db.query(IdentityProviderConfig).filter(IdentityProviderConfig.provider_type == provider_type, IdentityProviderConfig.enabled.is_(True)).first()
    config = row.config if row else {}
    if provider_type == "oidc":
        url = SsoService.build_oidc_url(config or {})
        return {
            "redirect_url": url,
            "message": "OIDC authorization URL generated from provider configuration template.",
        }
    if provider_type == "saml":
        return {
            "redirect_url": config.get("sso_url", "https://sso.example.com/saml/login?SAMLRequest=<generated-request>"),
            "message": "SAML SSO URL template generated. Replace metadata in identity provider config.",
        }
    return {
        "redirect_url": f"http://127.0.0.1:5173/login?sso={provider_type}",
        "message": f"{provider_type.upper()} login uses server-side bind/callback flow.",
    }


@router.get("/users/list", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return IdentityService.list_users(db)


@router.post("/users/save", response_model=UserOut)
def save_user(payload: UserUpsert, db: Session = Depends(get_db)):
    try:
        return IdentityService.save_local_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        user = IdentityService.delete_local_user(db, user_id)
        return {"message": "user marked resigned", "user": user}
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "user not found" else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.put("/users/{user_id}/permissions", response_model=UserOut)
def update_user_permissions(user_id: str, payload: UserPermissionUpdate, db: Session = Depends(get_db)):
    try:
        return IdentityService.update_user_permissions(db, user_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "user not found" else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/users/sync", response_model=SyncUsersResponse)
def sync_users(payload: SyncUsersRequest, db: Session = Depends(get_db)):
    try:
        created, updated, offboarded, users = IdentityService.sync_users(db, payload.provider_id, payload.users)
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
def save_permissions(payload: list[RolePermissionSave], db: Session = Depends(get_db)):
    try:
        return IdentityService.save_permissions(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/identity/providers", response_model=IdentityProviderOut)
def create_provider(payload: IdentityProviderSave, db: Session = Depends(get_db)):
    return IdentityService.save_provider(db, payload)


@router.put("/identity/providers/{provider_id}", response_model=IdentityProviderOut)
def update_provider(provider_id: int, payload: IdentityProviderSave, db: Session = Depends(get_db)):
    return IdentityService.save_provider(db, payload, provider_id)


@router.delete("/identity/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    try:
        IdentityService.delete_provider(db, provider_id)
        return {"message": "identity provider deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/identity/providers/{provider_id}/test", response_model=IdentityProviderOut)
def test_provider(provider_id: int, db: Session = Depends(get_db)):
    try:
        return IdentityService.test_provider(db, provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
