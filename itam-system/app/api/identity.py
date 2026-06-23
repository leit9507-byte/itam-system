from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    IdentityProviderOut,
    IdentityProviderSave,
    LoginRequest,
    LoginResponse,
    RolePermissionOut,
    SyncUsersRequest,
    SyncUsersResponse,
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
def sso_callback(provider_type: str, username: str, email: str | None = None, db: Session = Depends(get_db)):
    if provider_type not in {"oidc", "saml"}:
        raise HTTPException(status_code=400, detail="unsupported provider callback")
    return SsoService.callback_login(db, provider_type, username, email)


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


@router.post("/users/sync", response_model=SyncUsersResponse)
def sync_users(payload: SyncUsersRequest, db: Session = Depends(get_db)):
    created, updated, users = IdentityService.sync_users(db, payload.provider_id, payload.users)
    return {"created": created, "updated": updated, "users": users}


@router.get("/identity/providers", response_model=list[IdentityProviderOut])
def list_providers(db: Session = Depends(get_db)):
    return IdentityService.list_providers(db)


@router.get("/rbac/permissions", response_model=list[RolePermissionOut])
def list_permissions(db: Session = Depends(get_db)):
    return IdentityService.list_permissions(db)


@router.post("/identity/providers", response_model=IdentityProviderOut)
def create_provider(payload: IdentityProviderSave, db: Session = Depends(get_db)):
    return IdentityService.save_provider(db, payload)


@router.put("/identity/providers/{provider_id}", response_model=IdentityProviderOut)
def update_provider(provider_id: int, payload: IdentityProviderSave, db: Session = Depends(get_db)):
    return IdentityService.save_provider(db, payload, provider_id)


@router.post("/identity/providers/{provider_id}/test", response_model=IdentityProviderOut)
def test_provider(provider_id: int, db: Session = Depends(get_db)):
    try:
        return IdentityService.test_provider(db, provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
