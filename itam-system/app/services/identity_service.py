import logging
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.models.user import IdentityProviderConfig, RolePermission, UserDirectory
from app.schemas.user import IdentityProviderSave, RolePermissionSave, UserPermissionUpdate, UserUpsert


class IdentityService:
    _generated_seed_passwords: dict[str, str] = {}

    @staticmethod
    def ensure_seed(db: Session) -> None:
        settings = get_settings()
        IdentityService.validate_production_seed_passwords(settings)
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
                    password=IdentityService.seed_password("admin", settings.initial_admin_password),
                ),
            ]
            if settings.initial_auditor_password:
                seed_users.append(
                    UserUpsert(
                        user_id="U-AUDITOR",
                        username="auditor",
                        display_name="Audit User",
                        email="auditor@example.com",
                        dept_id="AUDIT",
                        dept_name="Audit Department",
                        role="auditor",
                        source="local",
                        password=settings.initial_auditor_password,
                    )
                )
            for item in seed_users:
                IdentityService.upsert_user(db, item, commit=False)

        IdentityService.remove_mock_providers(db)
        admin = db.query(UserDirectory).filter(UserDirectory.username == "admin").first()
        if admin and (not admin.password_hash or verify_password("admin", admin.password_hash)):
            admin.password_hash = hash_password(IdentityService.seed_password("admin", settings.initial_admin_password))
        auditor = db.query(UserDirectory).filter(UserDirectory.username == "auditor").first()
        if auditor and (not auditor.password_hash or verify_password("auditor", auditor.password_hash)):
            auditor.password_hash = hash_password(IdentityService.seed_password("auditor", settings.initial_auditor_password))
        for role, resource, actions in [
            ("user", "asset", ["read"]),
            ("user", "catalog", ["read"]),
            ("user", "file", ["read"]),
            ("asset_manager", "asset", ["read", "write"]),
            ("asset_manager", "file", ["read", "write"]),
            ("asset_manager", "catalog", ["read", "write"]),
            ("asset_manager", "purchase", ["read", "write"]),
            ("asset_manager", "repair", ["read", "write"]),
            ("asset_manager", "supplier", ["read", "write"]),
            ("asset_manager", "report", ["read"]),
            ("dept_manager", "asset", ["read", "write"]),
            ("dept_manager", "file", ["read", "write"]),
            ("dept_manager", "catalog", ["read"]),
            ("dept_manager", "purchase", ["read"]),
            ("dept_manager", "repair", ["read", "write"]),
            ("dept_manager", "supplier", ["read"]),
            ("dept_manager", "report", ["read"]),
            ("auditor", "asset", ["read"]),
            ("auditor", "file", ["read"]),
            ("auditor", "audit", ["read", "write"]),
            ("auditor", "report", ["read"]),
            ("auditor", "catalog", ["read"]),
            ("auditor", "purchase", ["read"]),
            ("auditor", "repair", ["read"]),
            ("auditor", "supplier", ["read"]),
        ]:
            for action in actions:
                existed = (
                    db.query(RolePermission)
                    .filter(RolePermission.role == role, RolePermission.resource == resource, RolePermission.action == action)
                    .first()
                )
                if not existed:
                    db.add(RolePermission(role=role, resource=resource, action=action, allowed=True))
        db.commit()

    @staticmethod
    def seed_password(username: str, configured: str | None) -> str:
        if configured:
            return configured
        if username not in IdentityService._generated_seed_passwords:
            password = secrets.token_urlsafe(18)
            IdentityService._generated_seed_passwords[username] = password
            logging.warning("Generated temporary password for seed user '%s': %s", username, password)
        return IdentityService._generated_seed_passwords[username]

    @staticmethod
    def validate_production_seed_passwords(settings) -> None:
        if not settings.production_mode:
            return
        if not settings.initial_admin_password:
            raise RuntimeError("Production requires INITIAL_ADMIN_PASSWORD")
        if settings.initial_auditor_password is None:
            raise RuntimeError("Production requires INITIAL_AUDITOR_PASSWORD")

    @staticmethod
    def list_users(db: Session) -> list[UserDirectory]:
        IdentityService.ensure_seed(db)
        return db.query(UserDirectory).order_by(UserDirectory.created_at.desc()).all()

    @staticmethod
    def upsert_user(db: Session, payload: UserUpsert, commit: bool = True, identity_provider_id: int | None = None) -> tuple[UserDirectory, bool]:
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
        if payload.source == "local":
            user.identity_provider_id = None
        elif identity_provider_id is not None:
            user.identity_provider_id = identity_provider_id
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
    def save_local_user(db: Session, payload: UserUpsert) -> UserDirectory:
        IdentityService.ensure_seed(db)
        clean_username = payload.username.strip()
        if not clean_username:
            raise ValueError("username is required")
        existed = db.query(UserDirectory).filter(UserDirectory.username == clean_username).first()
        if existed and existed.source != "local":
            raise ValueError("username already exists in external identity source")
        if not existed and not payload.password:
            raise ValueError("password is required for new local user")
        user, _ = IdentityService.upsert_user(
            db,
            payload.model_copy(update={"username": clean_username, "source": "local", "external_id": None}),
        )
        return user

    @staticmethod
    def delete_local_user(db: Session, user_id: str) -> UserDirectory:
        IdentityService.ensure_seed(db)
        user = db.get(UserDirectory, user_id)
        if not user:
            raise ValueError("user not found")
        if user.source != "local":
            raise ValueError("only local users can be deleted manually")
        if user.username == "admin":
            raise ValueError("built-in admin user cannot be deleted")
        if user.role == "admin":
            admin_count = db.query(UserDirectory).filter(UserDirectory.source == "local", UserDirectory.role == "admin").count()
            if admin_count <= 1:
                raise ValueError("cannot delete the last local admin user")
        user.status = "resigned"
        user.last_synced_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user_permissions(db: Session, user_id: str, payload: UserPermissionUpdate) -> UserDirectory:
        IdentityService.ensure_seed(db)
        user = db.get(UserDirectory, user_id)
        if not user:
            raise ValueError("user not found")

        next_role = payload.role.strip()
        next_status = payload.status.strip()
        if not next_role:
            raise ValueError("role is required")
        if not next_status:
            raise ValueError("status is required")

        if user.role == "admin" and next_role != "admin":
            admin_count = db.query(UserDirectory).filter(UserDirectory.role == "admin", UserDirectory.status == "active").count()
            if admin_count <= 1:
                raise ValueError("cannot remove the last active admin role")
        if user.role == "admin" and next_status != "active":
            active_admin_count = db.query(UserDirectory).filter(UserDirectory.role == "admin", UserDirectory.status == "active").count()
            if active_admin_count <= 1:
                raise ValueError("cannot disable the last active admin user")

        user.role = next_role
        user.status = next_status
        user.last_synced_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, username: str, password: str, provider: str = "local", remember_me: bool = False) -> dict:
        IdentityService.ensure_seed(db)
        settings = get_settings()
        expires_minutes = max(
            settings.jwt_remember_expire_days * 24 * 60 if remember_me else settings.jwt_expire_minutes,
            1,
        )
        if provider == "ldap":
            from app.services.sso_service import SsoService

            user = SsoService.ldap_authenticate(db, username, password)
            user.last_login_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            token = create_access_token(user.user_id, user.role, expires_minutes)
            return {"access_token": token, "token_type": "bearer", "expires_in": expires_minutes * 60, "user": user}
        if provider != "local":
            raise ValueError("only local and LDAP login are enabled")
        user = db.query(UserDirectory).filter(UserDirectory.username == username).first()
        now = datetime.utcnow()
        if not user:
            raise ValueError("invalid credentials")
        if user.status != "active":
            raise PermissionError("user is not active")
        if user.locked_until and user.locked_until > now:
            raise PermissionError(f"account locked until {user.locked_until.isoformat()}")
        if not verify_password(password, user.password_hash):
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
        token = create_access_token(user.user_id, user.role, expires_minutes)
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_minutes * 60, "user": user}

    @staticmethod
    def list_permissions(db: Session) -> list[RolePermission]:
        IdentityService.ensure_seed(db)
        return db.query(RolePermission).order_by(RolePermission.role, RolePermission.resource, RolePermission.action).all()

    @staticmethod
    def save_permissions(db: Session, payload: list[RolePermissionSave]) -> list[RolePermission]:
        IdentityService.ensure_seed(db)
        for item in payload:
            role = item.role.strip()
            resource = item.resource.strip()
            action = item.action.strip()
            if not role or not resource or not action:
                raise ValueError("role, resource and action are required")
            permission = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role == role,
                    RolePermission.resource == resource,
                    RolePermission.action == action,
                )
                .first()
            )
            if not permission:
                permission = RolePermission(role=role, resource=resource, action=action)
                db.add(permission)
            permission.allowed = item.allowed
        db.commit()
        return IdentityService.list_permissions(db)

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
    def delete_provider(db: Session, provider_id: int) -> None:
        provider = db.get(IdentityProviderConfig, provider_id)
        if not provider:
            raise ValueError("identity provider not found")
        db.delete(provider)
        db.commit()

    @staticmethod
    def test_provider(db: Session, provider_id: int) -> IdentityProviderConfig:
        provider = db.get(IdentityProviderConfig, provider_id)
        if not provider:
            raise ValueError("identity provider not found")

        required = {
            "ldap": ["host", "base_dn"],
            "feishu": ["app_id", "app_secret"],
        }.get(provider.provider_type, [])
        missing = [key for key in required if not (provider.config or {}).get(key)]
        if missing:
            provider.last_test_status = "failed"
            provider.last_test_message = f"Missing required fields: {', '.join(missing)}"
        elif provider.provider_type == "ldap":
            try:
                from app.services.sso_service import LdapClient

                provider.last_test_status = "success"
                provider.last_test_message = LdapClient.test(provider.config or {})
            except Exception as exc:
                provider.last_test_status = "failed"
                provider.last_test_message = str(exc)[:255]
        else:
            provider.last_test_status = "success"
            provider.last_test_message = f"{provider.provider_type.upper()} configuration looks valid"
        db.commit()
        db.refresh(provider)
        return provider

    @staticmethod
    def sync_users(db: Session, provider_id: int | None, users: list[UserUpsert]) -> tuple[int, int, int, list[UserDirectory]]:
        IdentityService.ensure_seed(db)
        provider = db.get(IdentityProviderConfig, provider_id) if provider_id else None
        source = provider.provider_type if provider else None
        sync_limit = int((provider.config or {}).get("sync_limit", 200)) if provider else 200
        if users:
            payloads = users
        elif provider and provider.provider_type == "ldap":
            from app.services.sso_service import LdapClient

            payloads = LdapClient.sync_users(provider.config or {}, limit=sync_limit)
        else:
            raise ValueError("No users to sync. Configure an LDAP identity source, or submit explicit users.")
        created = 0
        updated = 0
        offboarded = 0
        synced: list[UserDirectory] = []
        synced_external_ids = {item.external_id for item in payloads if item.external_id}
        synced_usernames = {item.username.casefold() for item in payloads if item.username}
        for payload in payloads:
            user, was_created = IdentityService.upsert_user(db, payload, commit=False, identity_provider_id=provider.id if provider else None)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
            synced.append(user)
        if source == "ldap" and len(payloads) < sync_limit:
            provider_count = db.query(IdentityProviderConfig).filter(IdentityProviderConfig.provider_type == "ldap").count()
            active_source_query = db.query(UserDirectory).filter(UserDirectory.source == source, UserDirectory.status == "active")
            if provider_count == 1:
                active_source_query = active_source_query.filter(
                    (UserDirectory.identity_provider_id == provider.id) | UserDirectory.identity_provider_id.is_(None)
                )
            else:
                active_source_query = active_source_query.filter(UserDirectory.identity_provider_id == provider.id)
            active_source_users = active_source_query.all()
            for user in active_source_users:
                if user.external_id in synced_external_ids or user.username.casefold() in synced_usernames:
                    continue
                user.status = "resigned"
                user.last_synced_at = datetime.utcnow()
                offboarded += 1
        db.commit()
        for user in synced:
            db.refresh(user)
        return created, updated, offboarded, synced

    @staticmethod
    def sync_enabled_ldap_providers(db: Session) -> tuple[int, int, int]:
        providers = (
            db.query(IdentityProviderConfig)
            .filter(IdentityProviderConfig.provider_type == "ldap", IdentityProviderConfig.enabled.is_(True))
            .all()
        )
        created = updated = offboarded = 0
        for provider in providers:
            provider_created, provider_updated, provider_offboarded, _ = IdentityService.sync_users(db, provider.id, [])
            created += provider_created
            updated += provider_updated
            offboarded += provider_offboarded
        return created, updated, offboarded

    @staticmethod
    def remove_mock_providers(db: Session) -> None:
        rows = (
            db.query(IdentityProviderConfig)
            .filter(
                IdentityProviderConfig.last_test_status == "mock",
                IdentityProviderConfig.name.in_(["Corporate LDAP", "Enterprise OIDC"]),
            )
            .all()
        )
        for row in rows:
            db.delete(row)
