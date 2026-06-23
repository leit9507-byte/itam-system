from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    IdentityProviderOut,
    IdentityProviderSave,
    LoginRequest,
    LoginResponse,
    SyncUsersRequest,
    SyncUsersResponse,
    UserOut,
    UserUpsert,
)
from app.services.identity_service import IdentityService


router = APIRouter(tags=["Identity"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    IdentityService.ensure_seed(db)
    from app.models.user import UserDirectory

    user = db.query(UserDirectory).filter(UserDirectory.username == payload.username).first()
    if not user:
        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                username=payload.username,
                display_name=payload.username,
                email=f"{payload.username}@example.com",
                source=payload.provider,
                external_id=f"{payload.provider}:{payload.username}",
            ),
        )
    return {"access_token": f"mock-token-{payload.provider}-{user.username}", "token_type": "bearer", "user": user}


@router.get("/auth/sso/{provider_type}/start")
def start_sso(provider_type: str):
    return {
        "provider": provider_type,
        "redirect_url": f"http://127.0.0.1:5173/permission?sso={provider_type}&mock=1",
        "message": "Mock SSO redirect. Replace this with real OIDC/SAML authorization URL in production.",
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
