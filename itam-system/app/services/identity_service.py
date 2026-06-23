from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.models.user import IdentityProviderConfig, RolePermission, UserDirectory
from app.schemas.user import IdentityProviderSave, UserUpsert


class IdentityService:
    @staticmethod
    def ensure_seed(db: Session) -> None:
        if not db.query(UserDirectory).first():
            seed_users = [
                UserUpsert(
                    user_id="U-ADMIN",
                    username="admin",
                    display_name="ITAM Admin",
                    email="admin@example.com",
                    dept_id="IT",
                    dept_name="IT Department",
                    role="admin",
                    source="local",
                    password="admin",
                ),
                UserUpsert(
                    user_id="U-AUDITOR",
                    username="auditor",
                    display_name="Audit User",
                    email="auditor@example.com",
                    dept_id="AUDIT",
                    dept_name="Audit Department",
                    role="auditor",
                    source="local",
                    password="auditor",
                ),
            ]
            for item in seed_users:
                IdentityService.upsert_user(db, item, commit=False)

        if not db.query(IdentityProviderConfig).first():
            db.add(
                IdentityProviderConfig(
                    name="Corporate LDAP",
                    provider_type="ldap",
                    enabled=True,
                    config={
                        "host": "ldap://ldap.example.com",
                        "base_dn": "dc=example,dc=com",
                        "user_filter": "(objectClass=person)",
                        "username_attr": "sAMAccountName",
                    },
                    last_test_status="mock",
                    last_test_message="Waiting for real LDAP configuration",
                )
            )
            db.add(
                IdentityProviderConfig(
                    name="Enterprise OIDC",
                    provider_type="oidc",
                    enabled=False,
                    config={
                        "issuer": "https://sso.example.com",
                        "client_id": "itam-dashboard",
                        "scopes": "openid profile email",
                    },
                    last_test_status="mock",
                    last_test_message="Waiting for real SSO configuration",
                )
            )
        admin = db.query(UserDirectory).filter(UserDirectory.username == "admin").first()
        if admin and not admin.password_hash:
            admin.password_hash = hash_password("admin")
        auditor = db.query(UserDirectory).filter(UserDirectory.username == "auditor").first()
        if auditor and not auditor.password_hash:
            auditor.password_hash = hash_password("auditor")
        if not db.query(RolePermission).first():
            for role, resource, actions in [
                ("user", "asset", ["read"]),
                ("user", "catalog", ["read"]),
                ("user", "purchase", ["read"]),
                ("auditor", "asset", ["read"]),
                ("auditor", "audit", ["read", "write"]),
                ("auditor", "report", ["read"]),
                ("auditor", "catalog", ["read"]),
            ]:
                for action in actions:
                    db.add(RolePermission(role=role, resource=resource, action=action, allowed=True))
        db.commit()

    @staticmethod
    def list_users(db: Session) -> list[UserDirectory]:
        IdentityService.ensure_seed(db)
        return db.query(UserDirectory).order_by(UserDirectory.created_at.desc()).all()

    @staticmethod
    def upsert_user(db: Session, payload: UserUpsert, commit: bool = True) -> tuple[UserDirectory, bool]:
        user_id = payload.user_id or payload.external_id or f"U-{uuid4().hex[:10].upper()}"
        user = db.get(UserDirectory, user_id)
        created = False
        if not user:
            user = db.query(UserDirectory).filter(UserDirectory.username == payload.username).first()
        if not user:
            user = UserDirectory(user_id=user_id, created_at=datetime.utcnow())
            db.add(user)
            created = True

        user.username = payload.username
        user.display_name = payload.display_name
        user.email = payload.email
        user.dept_id = payload.dept_id
        user.dept_name = payload.dept_name
        user.role = payload.role
        user.source = payload.source
        user.status = payload.status
        user.external_id = payload.external_id
        if payload.password:
            user.password_hash = hash_password(payload.password)
        user.last_synced_at = datetime.utcnow()

        if commit:
            db.commit()
            db.refresh(user)
        return user, created

    @staticmethod
    def authenticate(db: Session, username: str, password: str, provider: str = "local") -> dict:
        IdentityService.ensure_seed(db)
        if provider == "ldap":
            from app.services.sso_service import SsoService

            user = SsoService.ldap_authenticate(db, username, password)
            user.last_login_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            token = create_access_token(user.user_id, user.role)
            return {"access_token": token, "token_type": "bearer", "expires_in": get_settings().jwt_expire_minutes * 60, "user": user}
        if provider in {"oidc", "saml"}:
            raise ValueError(f"{provider} login must start from SSO redirect/callback")
        settings = get_settings()
        user = db.query(UserDirectory).filter(UserDirectory.username == username).first()
        now = datetime.utcnow()
        if not user:
            raise ValueError("invalid credentials")
        if user.locked_until and user.locked_until > now:
            raise PermissionError(f"account locked until {user.locked_until.isoformat()}")
        if provider == "local" and not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_lock_threshold:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            db.commit()
            raise ValueError("invalid credentials")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        db.commit()
        db.refresh(user)
        token = create_access_token(user.user_id, user.role)
        return {"access_token": token, "token_type": "bearer", "expires_in": settings.jwt_expire_minutes * 60, "user": user}

    @staticmethod
    def list_permissions(db: Session) -> list[RolePermission]:
        IdentityService.ensure_seed(db)
        return db.query(RolePermission).order_by(RolePermission.role, RolePermission.resource, RolePermission.action).all()

    @staticmethod
    def list_providers(db: Session) -> list[IdentityProviderConfig]:
        IdentityService.ensure_seed(db)
        return db.query(IdentityProviderConfig).order_by(IdentityProviderConfig.id.asc()).all()

    @staticmethod
    def save_provider(db: Session, payload: IdentityProviderSave, provider_id: int | None = None) -> IdentityProviderConfig:
        provider = db.get(IdentityProviderConfig, provider_id) if provider_id else None
        if not provider:
            provider = IdentityProviderConfig()
            db.add(provider)

        provider.name = payload.name
        provider.provider_type = payload.provider_type
        provider.enabled = payload.enabled
        provider.config = payload.config
        provider.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(provider)
        return provider

    @staticmethod
    def test_provider(db: Session, provider_id: int) -> IdentityProviderConfig:
        provider = db.get(IdentityProviderConfig, provider_id)
        if not provider:
            raise ValueError("identity provider not found")

        required = {
            "ldap": ["host", "base_dn"],
            "oidc": ["issuer", "client_id"],
            "saml": ["sso_url", "entity_id"],
            "feishu": ["app_id"],
            "wechat_work": ["corp_id"],
            "local": [],
        }.get(provider.provider_type, [])
        missing = [key for key in required if not (provider.config or {}).get(key)]
        provider.last_test_status = "failed" if missing else "success"
        provider.last_test_message = (
            f"Missing required fields: {', '.join(missing)}"
            if missing
            else f"{provider.provider_type.upper()} configuration looks valid in mock test"
        )
        db.commit()
        db.refresh(provider)
        return provider

    @staticmethod
    def sync_users(db: Session, provider_id: int | None, users: list[UserUpsert]) -> tuple[int, int, list[UserDirectory]]:
        IdentityService.ensure_seed(db)
        provider = db.get(IdentityProviderConfig, provider_id) if provider_id else None
        payloads = users or IdentityService.mock_provider_users(provider)
        created = 0
        updated = 0
        synced: list[UserDirectory] = []
        for payload in payloads:
            user, was_created = IdentityService.upsert_user(db, payload, commit=False)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
            synced.append(user)
        db.commit()
        for user in synced:
            db.refresh(user)
        return created, updated, synced

    @staticmethod
    def mock_provider_users(provider: IdentityProviderConfig | None) -> list[UserUpsert]:
        source = provider.provider_type if provider else "ldap"
        return [
            UserUpsert(
                user_id=f"{source.upper()}-001",
                username="zhang.wei",
                display_name="Zhang Wei",
                email="zhang.wei@example.com",
                dept_id="RD",
                dept_name="R&D Department",
                role="user",
                source=source,
                external_id=f"{source}-001",
            ),
            UserUpsert(
                user_id=f"{source.upper()}-002",
                username="li.na",
                display_name="Li Na",
                email="li.na@example.com",
                dept_id="FIN",
                dept_name="Finance Department",
                role="auditor",
                source=source,
                external_id=f"{source}-002",
            ),
        ]
