from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.models.user import IdentityProviderConfig, UserDirectory
from app.schemas.user import UserUpsert
from app.services.identity_service import IdentityService


class SsoService:
    @staticmethod
    def ldap_authenticate(db: Session, username: str, password: str) -> UserDirectory:
        provider = db.query(IdentityProviderConfig).filter(IdentityProviderConfig.provider_type == "ldap", IdentityProviderConfig.enabled.is_(True)).first()
        if not provider:
            raise ValueError("LDAP provider is not configured")
        config = provider.config or {}
        try:
            from ldap3 import Connection, Server
        except ImportError as exc:
            raise ValueError("ldap3 is not installed") from exc

        user_dn_template = config.get("user_dn_template")
        bind_user = user_dn_template.format(username=username) if user_dn_template else username
        server = Server(config["host"], get_info=None)
        conn = Connection(server, user=bind_user, password=password, auto_bind=True)
        conn.unbind()

        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                username=username,
                display_name=username,
                email=f"{username}@ldap.local",
                role=config.get("default_role", "user"),
                source="ldap",
                external_id=f"ldap:{username}",
            ),
        )
        return user

    @staticmethod
    def build_oidc_url(config: dict) -> str:
        params = {
            "response_type": "code",
            "client_id": config.get("client_id", "itam-dashboard"),
            "redirect_uri": config.get("redirect_uri", "http://127.0.0.1:8000/auth/callback/oidc"),
            "scope": config.get("scopes", "openid profile email"),
            "state": "itam",
        }
        return f"{config.get('authorization_endpoint', config.get('issuer', '').rstrip('/') + '/authorize')}?{urlencode(params)}"

    @staticmethod
    def callback_login(db: Session, provider_type: str, username: str, email: str | None = None) -> dict:
        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                username=username,
                display_name=username,
                email=email,
                role="user",
                source=provider_type,
                external_id=f"{provider_type}:{username}",
            ),
        )
        from app.core.auth import create_access_token
        from app.core.config import get_settings

        return {
            "access_token": create_access_token(user.user_id, user.role),
            "token_type": "bearer",
            "expires_in": get_settings().jwt_expire_minutes * 60,
            "user": user,
        }
