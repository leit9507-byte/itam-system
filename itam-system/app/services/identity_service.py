from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import IdentityProviderConfig, UserDirectory
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
        user.last_synced_at = datetime.utcnow()

        if commit:
            db.commit()
            db.refresh(user)
        return user, created

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
