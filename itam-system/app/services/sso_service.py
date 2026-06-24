import ssl
from urllib.parse import urlparse, urlencode

from sqlalchemy.orm import Session

from app.models.user import IdentityProviderConfig, UserDirectory
from app.schemas.user import UserUpsert
from app.services.identity_service import IdentityService


class SsoService:
    @staticmethod
    def ldap_authenticate(db: Session, username: str, password: str) -> UserDirectory:
        if not password:
            raise ValueError("LDAP password is required")
        provider = (
            db.query(IdentityProviderConfig)
            .filter(IdentityProviderConfig.provider_type == "ldap", IdentityProviderConfig.enabled.is_(True))
            .order_by(IdentityProviderConfig.id.desc())
            .first()
        )
        if not provider:
            raise ValueError("LDAP provider is not configured")

        config = provider.config or {}
        try:
            user_dn, attrs = LdapClient.resolve_user_dn(config, username)
            LdapClient.bind(config, user_dn, password)
        except Exception as exc:
            raise ValueError(f"LDAP bind failed: {exc}") from exc

        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                username=username,
                display_name=attrs.get("display_name") or username,
                email=attrs.get("email"),
                dept_id=attrs.get("dept_id"),
                dept_name=attrs.get("dept_name"),
                role=config.get("default_role", "user"),
                source="ldap",
                external_id=f"ldap:{attrs.get('dn') or user_dn}",
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


class LdapClient:
    @staticmethod
    def load():
        try:
            from ldap3 import ALL, AUTO_BIND_NO_TLS, AUTO_BIND_TLS_BEFORE_BIND, NTLM, SIMPLE, SUBTREE, Connection, Server, Tls
        except ImportError as exc:
            raise ValueError("ldap3 is not installed") from exc
        return {
            "ALL": ALL,
            "AUTO_BIND_NO_TLS": AUTO_BIND_NO_TLS,
            "AUTO_BIND_TLS_BEFORE_BIND": AUTO_BIND_TLS_BEFORE_BIND,
            "NTLM": NTLM,
            "SIMPLE": SIMPLE,
            "SUBTREE": SUBTREE,
            "Connection": Connection,
            "Server": Server,
            "Tls": Tls,
        }

    @staticmethod
    def server(config: dict):
        ldap = LdapClient.load()
        host, port, use_ssl = LdapClient.normalize_host(config)
        tls = None
        if config.get("use_ssl") or config.get("start_tls"):
            validate = ssl.CERT_REQUIRED if config.get("tls_validate", True) else ssl.CERT_NONE
            tls = ldap["Tls"](validate=validate)
        return ldap["Server"](
            host,
            port=port,
            use_ssl=use_ssl,
            connect_timeout=int(config.get("connect_timeout", 5)),
            get_info=ldap["ALL"],
            tls=tls,
        )

    @staticmethod
    def auth_method(config: dict):
        ldap = LdapClient.load()
        return ldap["NTLM"] if str(config.get("authentication", "SIMPLE")).upper() == "NTLM" else ldap["SIMPLE"]

    @staticmethod
    def bind(config: dict, user: str | None = None, password: str | None = None):
        ldap = LdapClient.load()
        auto_bind = ldap["AUTO_BIND_TLS_BEFORE_BIND"] if config.get("start_tls") else ldap["AUTO_BIND_NO_TLS"]
        return ldap["Connection"](
            LdapClient.server(config),
            user=user,
            password=password,
            authentication=LdapClient.auth_method(config),
            receive_timeout=int(config.get("receive_timeout", 8)),
            auto_bind=auto_bind,
        )

    @staticmethod
    def service_connection(config: dict):
        bind_dn = config.get("bind_dn") or config.get("service_account")
        bind_password = config.get("bind_password") or config.get("service_password")
        if not bind_dn:
            raise ValueError("bind_dn is required when user_dn_template is not configured")
        return LdapClient.bind(config, bind_dn, bind_password)

    @staticmethod
    def resolve_user_dn(config: dict, username: str) -> tuple[str, dict]:
        user_dn_template = config.get("user_dn_template")
        if user_dn_template:
            user_dn = user_dn_template.format(username=username)
            return user_dn, {"dn": user_dn, "display_name": username}

        base_dn = config.get("base_dn")
        if not base_dn:
            raise ValueError("base_dn is required")

        username_attr = config.get("username_attr", "sAMAccountName")
        user_filter = config.get("user_filter") or f"({username_attr}={{username}})"
        search_filter = user_filter.format(username=LdapClient.escape_filter(username))
        attributes = LdapClient.attributes(config)

        conn = LdapClient.service_connection(config)
        try:
            ldap = LdapClient.load()
            if not conn.search(base_dn, search_filter, search_scope=ldap["SUBTREE"], attributes=attributes, size_limit=2):
                raise ValueError(f"user not found by filter {search_filter}")
            if len(conn.entries) > 1:
                raise ValueError(f"multiple users matched filter {search_filter}")
            entry = conn.entries[0]
            return entry.entry_dn, LdapClient.entry_attrs(entry, config)
        finally:
            conn.unbind()

    @staticmethod
    def test(config: dict) -> str:
        host, port, use_ssl = LdapClient.normalize_host(config)
        mode = "service bind" if config.get("bind_dn") else "direct user bind" if config.get("user_dn_template") else "anonymous bind"
        if config.get("user_dn_template") and not config.get("bind_dn"):
            LdapClient.server(config)
            return f"LDAP configuration ready for direct user bind: {host}:{port}, ssl={use_ssl}"

        conn = LdapClient.service_connection(config) if config.get("bind_dn") else LdapClient.bind(config)
        try:
            base_dn = config.get("base_dn")
            test_username = config.get("test_username")
            if base_dn and test_username:
                user_dn, _ = LdapClient.resolve_user_dn(config, test_username)
                return f"LDAP {mode} success on {host}:{port}, test user resolved: {user_dn}"
            return f"LDAP {mode} success on {host}:{port}, ssl={use_ssl}"
        finally:
            conn.unbind()

    @staticmethod
    def sync_users(config: dict, limit: int = 200) -> list[UserUpsert]:
        base_dn = config.get("base_dn")
        if not base_dn:
            raise ValueError("base_dn is required")

        conn = LdapClient.service_connection(config)
        try:
            ldap = LdapClient.load()
            search_filter = config.get("sync_filter") or config.get("user_filter") or "(objectClass=person)"
            attributes = LdapClient.attributes(config)
            conn.search(base_dn, search_filter, search_scope=ldap["SUBTREE"], attributes=attributes, size_limit=limit)
            users: list[UserUpsert] = []
            username_attr = config.get("username_attr", "sAMAccountName")
            for entry in conn.entries:
                attrs = LdapClient.entry_attrs(entry, config)
                username = LdapClient.entry_value(entry, username_attr)
                if not username:
                    continue
                users.append(
                    UserUpsert(
                        username=username,
                        display_name=attrs.get("display_name") or username,
                        email=attrs.get("email"),
                        dept_id=attrs.get("dept_id"),
                        dept_name=attrs.get("dept_name"),
                        role=config.get("default_role", "user"),
                        source="ldap",
                        external_id=f"ldap:{entry.entry_dn}",
                    )
                )
            return users
        finally:
            conn.unbind()

    @staticmethod
    def attributes(config: dict) -> list[str]:
        return list(
            {
                config.get("username_attr", "sAMAccountName"),
                config.get("display_name_attr", "displayName"),
                config.get("email_attr", "mail"),
                config.get("dept_id_attr", "departmentNumber"),
                config.get("dept_name_attr", "department"),
            }
        )

    @staticmethod
    def entry_attrs(entry, config: dict) -> dict:
        return {
            "dn": entry.entry_dn,
            "display_name": LdapClient.entry_value(entry, config.get("display_name_attr", "displayName")),
            "email": LdapClient.entry_value(entry, config.get("email_attr", "mail")),
            "dept_id": LdapClient.entry_value(entry, config.get("dept_id_attr", "departmentNumber")),
            "dept_name": LdapClient.entry_value(entry, config.get("dept_name_attr", "department")),
        }

    @staticmethod
    def entry_value(entry, attr: str):
        if not hasattr(entry, attr):
            return None
        value = getattr(entry, attr).value
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @staticmethod
    def escape_filter(value: str) -> str:
        return (
            value.replace("\\", r"\5c")
            .replace("*", r"\2a")
            .replace("(", r"\28")
            .replace(")", r"\29")
            .replace("\x00", r"\00")
        )

    @staticmethod
    def normalize_host(config: dict) -> tuple[str, int | None, bool]:
        raw_host = str(config.get("host") or "").strip()
        if not raw_host:
            raise ValueError("host is required")
        parsed = urlparse(raw_host if "://" in raw_host else f"ldap://{raw_host}")
        host = parsed.hostname or raw_host
        use_ssl = bool(config.get("use_ssl", parsed.scheme == "ldaps"))
        port = config.get("port") or parsed.port
        if port is None:
            port = 636 if use_ssl else 389
        return host, int(port), use_ssl
