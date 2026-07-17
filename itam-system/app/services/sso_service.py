import re
import ssl
import json
import hashlib
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen

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
            identity_provider_id=provider.id,
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
    def build_feishu_url(config: dict, state: str | None = None, redirect_uri: str | None = None) -> str:
        app_id = config.get("app_id")
        if not app_id:
            raise ValueError("Feishu provider missing app_id")
        redirect_uri = redirect_uri or config.get("redirect_uri") or "http://127.0.0.1:5173/login"
        params = {
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state or config.get("state") or "itam",
        }
        return f"https://open.feishu.cn/open-apis/authen/v1/authorize?{urlencode(params)}"

    @staticmethod
    def oidc_callback_login(db: Session, code: str, state: str | None = None) -> dict:
        provider = (
            db.query(IdentityProviderConfig)
            .filter(IdentityProviderConfig.provider_type == "oidc", IdentityProviderConfig.enabled.is_(True))
            .order_by(IdentityProviderConfig.id.desc())
            .first()
        )
        if not provider:
            raise ValueError("OIDC provider is not configured")
        config = provider.config or {}
        expected_state = config.get("state") or "itam"
        if state and state != expected_state:
            raise ValueError("OIDC state mismatch")

        for key in ("token_endpoint", "userinfo_endpoint", "client_id", "client_secret"):
            if not config.get(key):
                raise ValueError(f"OIDC provider missing {key}")

        token_payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.get("redirect_uri", "http://127.0.0.1:8000/auth/callback/oidc"),
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        token_data = SsoService.post_form(config["token_endpoint"], token_payload)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("OIDC token response missing access_token")

        userinfo = SsoService.get_json(config["userinfo_endpoint"], {"Authorization": f"Bearer {access_token}"})
        subject = userinfo.get("sub")
        username = userinfo.get("preferred_username") or userinfo.get("email") or subject
        if not subject or not username:
            raise ValueError("OIDC userinfo missing subject or username")

        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                username=username,
                display_name=userinfo.get("name") or username,
                email=userinfo.get("email"),
                role=config.get("default_role", "user"),
                source="oidc",
                external_id=f"oidc:{subject}",
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

    @staticmethod
    def feishu_callback_login(db: Session, code: str, state: str | None = None) -> dict:
        return SsoService.feishu_login_by_code(db, code, state=state, source="feishu-sso")

    @staticmethod
    def feishu_login_by_code(db: Session, code: str, state: str | None = None, source: str = "feishu-webapp") -> dict:
        provider = (
            db.query(IdentityProviderConfig)
            .filter(IdentityProviderConfig.provider_type == "feishu", IdentityProviderConfig.enabled.is_(True))
            .order_by(IdentityProviderConfig.id.desc())
            .first()
        )
        if not provider:
            raise ValueError("Feishu provider is not configured")
        config = provider.config or {}
        token = FeishuClient.tenant_access_token(config)
        user_token = FeishuClient.user_access_token(token, code)
        userinfo = FeishuClient.user_info(user_token)
        external_id = userinfo.get("user_id") or userinfo.get("open_id") or userinfo.get("union_id")
        if not external_id:
            raise ValueError("Feishu user info missing user_id/open_id")
        username = str(userinfo.get("email") or userinfo.get("mobile") or external_id)[:64]
        user, _ = IdentityService.upsert_user(
            db,
            UserUpsert(
                user_id=FeishuClient.local_user_id(external_id),
                username=username,
                display_name=userinfo.get("name") or userinfo.get("en_name") or username,
                email=userinfo.get("email"),
                role=config.get("default_role", "user"),
                source="feishu",
                external_id=f"feishu:{external_id}",
            ),
        )
        from app.core.auth import create_access_token
        from app.core.config import get_settings

        return {
            "access_token": create_access_token(user.user_id, user.role),
            "token_type": "bearer",
            "expires_in": get_settings().jwt_expire_minutes * 60,
            "user": user,
            "source": source,
        }

    @staticmethod
    def post_form(url: str, payload: dict) -> dict:
        data = urlencode(payload).encode()
        request = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError(f"OIDC token request failed: {exc}") from exc

    @staticmethod
    def get_json(url: str, headers: dict | None = None) -> dict:
        request = Request(url, headers={"Accept": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError(f"OIDC userinfo request failed: {exc}") from exc


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

        attributes = LdapClient.attributes(config)

        conn = LdapClient.service_connection(config)
        try:
            search_filter, entries = LdapClient.search_user_with_fallback(conn, base_dn, config, username, attributes)
            if not entries:
                raise ValueError(f"user not found by filter {search_filter}")
            if len(entries) > 1:
                raise ValueError(f"multiple users matched filter {search_filter}")
            entry = entries[0]
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
            search_filter = config.get("sync_filter") or config.get("user_filter") or "(objectClass=person)"
            attributes = LdapClient.attributes(config)
            entries = LdapClient.search(conn, base_dn, search_filter, attributes, size_limit=limit)
            users: list[UserUpsert] = []
            username_attrs = LdapClient.username_candidates(config)
            for entry in entries:
                attrs = LdapClient.entry_attrs(entry, config)
                username = LdapClient.first_entry_value(entry, username_attrs)
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
        attrs = [
            *LdapClient.username_candidates(config),
            config.get("display_name_attr", "displayName"),
            config.get("email_attr", "mail"),
            config.get("dept_id_attr"),
            config.get("dept_name_attr"),
        ]
        return list(dict.fromkeys(attr for attr in attrs if attr))

    @staticmethod
    def entry_attrs(entry, config: dict) -> dict:
        return {
            "dn": entry.entry_dn,
            "display_name": LdapClient.entry_value(entry, config.get("display_name_attr", "displayName")),
            "email": LdapClient.entry_value(entry, config.get("email_attr", "mail")),
            "dept_id": LdapClient.entry_value(entry, config.get("dept_id_attr")) if config.get("dept_id_attr") else None,
            "dept_name": LdapClient.entry_value(entry, config.get("dept_name_attr")) if config.get("dept_name_attr") else None,
        }

    @staticmethod
    def entry_value(entry, attr: str):
        if not attr:
            return None
        if not hasattr(entry, attr):
            return None
        value = getattr(entry, attr).value
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @staticmethod
    def first_entry_value(entry, attrs: list[str]):
        for attr in attrs:
            value = LdapClient.entry_value(entry, attr)
            if value not in (None, ""):
                return value
        return None

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

    @staticmethod
    def search(conn, base_dn: str, search_filter: str, attributes: list[str], size_limit: int):
        ldap = LdapClient.load()
        remaining = list(attributes)
        while True:
            try:
                ok = conn.search(base_dn, search_filter, search_scope=ldap["SUBTREE"], attributes=remaining, size_limit=size_limit)
                return list(conn.entries) if ok else []
            except Exception as exc:
                bad_attr = LdapClient.invalid_attribute_from_error(exc)
                if not bad_attr or bad_attr not in remaining:
                    raise ValueError(LdapClient.friendly_ldap_error(exc)) from exc
                remaining.remove(bad_attr)
                if not remaining:
                    raise ValueError(f"All requested LDAP attributes are invalid. Last invalid attribute: {bad_attr}") from exc

    @staticmethod
    def search_user_with_fallback(conn, base_dn: str, config: dict, username: str, attributes: list[str]):
        escaped = LdapClient.escape_filter(username)
        filters = LdapClient.user_filters(config, escaped)
        last_error: Exception | None = None
        for search_filter in filters:
            try:
                return search_filter, LdapClient.search(conn, base_dn, search_filter, attributes, size_limit=2)
            except ValueError as exc:
                last_error = exc
                bad_attr = LdapClient.invalid_attribute_from_error(exc)
                if not bad_attr or bad_attr not in search_filter:
                    raise
        if last_error:
            raise ValueError(
                f"LDAP username filter attributes are invalid. Tried: {', '.join(filters)}. "
                "For OpenLDAP use uid/cn/mail; for AD use sAMAccountName/userPrincipalName."
            ) from last_error
        return "", []

    @staticmethod
    def user_filters(config: dict, escaped_username: str) -> list[str]:
        configured_filter = config.get("user_filter")
        filters: list[str] = []
        if configured_filter:
            filters.append(configured_filter.format(username=escaped_username))
        for attr in LdapClient.username_candidates(config):
            filters.append(f"({attr}={escaped_username})")
        return list(dict.fromkeys(filters))

    @staticmethod
    def username_candidates(config: dict) -> list[str]:
        configured = config.get("username_attr")
        candidates = [
            configured,
            "uid",
            "cn",
            "mail",
            "userPrincipalName",
            "sAMAccountName",
        ]
        return list(dict.fromkeys(attr for attr in candidates if attr))

    @staticmethod
    def invalid_attribute_from_error(exc: Exception) -> str | None:
        text = str(exc)
        match = re.search(r"invalid attribute type\s+([A-Za-z0-9_.;-]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r"Invalid LDAP attribute '([^']+)'", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def friendly_ldap_error(exc: Exception) -> str:
        bad_attr = LdapClient.invalid_attribute_from_error(exc)
        if bad_attr:
            return f"Invalid LDAP attribute '{bad_attr}'. Remove it from config or replace it with a real schema attribute such as ou/cn/mail."
        return str(exc)


class FeishuClient:
    API_BASE = "https://open.feishu.cn/open-apis"

    @staticmethod
    def test(config: dict) -> str:
        token = FeishuClient.tenant_access_token(config)
        if FeishuClient.login_only(config):
            return "Feishu login configuration success. Organization sync is disabled."
        manual_departments = FeishuClient.configured_department_ids(config)
        try:
            if manual_departments and not FeishuClient.discover_child_departments(config):
                users = FeishuClient.users_by_department(config, token, manual_departments[0], limit=1)
                return f"Feishu connection success. Department {manual_departments[0]} users visible: {len(users)}"
            departments = FeishuClient.department_children(config, token, manual_departments[0] if manual_departments else FeishuClient.root_department_id(config), page_size=1, limit=1)
            return f"Feishu connection success. Department children visible: {len(departments)}"
        except ValueError as exc:
            if FeishuClient.is_no_dept_authority(exc):
                raise ValueError(
                    "飞书应用没有当前部门的数据权限。可在系统里填写“指定部门 ID 列表”，并关闭“自动同步子部门”；"
                    "如果要从根部门 0 同步，则飞书应用需要全通讯录/根部门可见范围。"
                ) from exc
            raise

    @staticmethod
    def sync_users(config: dict, limit: int = 200) -> list[UserUpsert]:
        token = FeishuClient.tenant_access_token(config)
        department_names: dict[str, str] = {}
        department_ids = FeishuClient.collect_department_ids(config, token, department_names, limit)
        users: list[UserUpsert] = []
        seen: set[str] = set()
        for department_id in department_ids:
            for item in FeishuClient.users_by_department(config, token, department_id, limit=max(limit - len(users), 1)):
                external_id = item.get("user_id") or item.get("open_id") or item.get("union_id")
                if not external_id or external_id in seen:
                    continue
                seen.add(external_id)
                dept_ids = item.get("department_ids") or [department_id]
                dept_id = dept_ids[0] if dept_ids else department_id
                users.append(
                    UserUpsert(
                        user_id=FeishuClient.local_user_id(external_id),
                        username=str(item.get("email") or item.get("mobile") or external_id)[:64],
                        display_name=item.get("name") or item.get("en_name") or external_id,
                        email=item.get("email"),
                        dept_id=dept_id,
                        dept_name=department_names.get(dept_id) or dept_id,
                        role=config.get("default_role", "user"),
                        source="feishu",
                        external_id=f"feishu:{external_id}",
                        status=FeishuClient.user_status(item),
                    )
                )
                if len(users) >= limit:
                    return users
        return users

    @staticmethod
    def collect_department_ids(config: dict, token: str, department_names: dict[str, str], limit: int) -> list[str]:
        start_ids = FeishuClient.configured_department_ids(config) or [FeishuClient.root_department_id(config)]
        if not FeishuClient.discover_child_departments(config):
            return start_ids
        queue = list(start_ids)
        result = list(dict.fromkeys(start_ids))
        max_departments = int(config.get("department_limit") or limit or 200)
        while queue and len(result) < max_departments:
            current = queue.pop(0)
            try:
                children = FeishuClient.department_children(config, token, current)
            except ValueError as exc:
                if FeishuClient.is_no_dept_authority(exc) and FeishuClient.configured_department_ids(config):
                    continue
                raise
            for dept in children:
                dept_id = dept.get("open_department_id") or dept.get("department_id")
                if not dept_id or dept_id in result:
                    continue
                department_names[dept_id] = dept.get("name") or dept_id
                result.append(dept_id)
                queue.append(dept_id)
                if len(result) >= max_departments:
                    break
        return result

    @staticmethod
    def tenant_access_token(config: dict) -> str:
        app_id = config.get("app_id")
        app_secret = config.get("app_secret") or config.get("tenant_key")
        if not app_id or not app_secret:
            raise ValueError("app_id and app_secret are required")
        data = FeishuClient.request_json(
            "POST",
            "/auth/v3/tenant_access_token/internal",
            body={"app_id": app_id, "app_secret": app_secret},
        )
        token = data.get("tenant_access_token")
        if not token:
            raise ValueError("Feishu tenant_access_token missing in response")
        return token

    @staticmethod
    def user_access_token(tenant_access_token: str, code: str) -> str:
        data = FeishuClient.request_json(
            "POST",
            "/authen/v1/access_token",
            token=tenant_access_token,
            body={"grant_type": "authorization_code", "code": code},
        )
        payload = data.get("data") or data
        access_token = payload.get("access_token") or payload.get("user_access_token")
        if not access_token:
            raise ValueError("Feishu user access_token missing in response")
        return access_token

    @staticmethod
    def user_info(user_access_token: str) -> dict:
        data = FeishuClient.request_json("GET", "/authen/v1/user_info", token=user_access_token)
        return data.get("data") or data

    @staticmethod
    def department_children(config: dict, token: str, department_id: str, page_size: int | None = None, limit: int | None = None) -> list[dict]:
        query = {
            "department_id_type": config.get("department_id_type", "open_department_id"),
            "page_size": page_size or int(config.get("page_size") or 50),
        }
        return FeishuClient.paged_get(
            f"/contact/v3/departments/{department_id}/children",
            token,
            query,
            item_key="items",
            limit=limit,
        )

    @staticmethod
    def users_by_department(config: dict, token: str, department_id: str, limit: int) -> list[dict]:
        query = {
            "department_id": department_id,
            "department_id_type": config.get("department_id_type", "open_department_id"),
            "user_id_type": config.get("user_id_type", "user_id"),
            "page_size": min(int(config.get("page_size") or 50), max(limit, 1)),
        }
        return FeishuClient.paged_get("/contact/v3/users/find_by_department", token, query, item_key="items", limit=limit)

    @staticmethod
    def paged_get(path: str, token: str, query: dict, item_key: str, limit: int | None = None) -> list[dict]:
        items: list[dict] = []
        page_token = ""
        while True:
            params = {**query}
            if page_token:
                params["page_token"] = page_token
            data = FeishuClient.request_json("GET", path, token=token, query=params)
            page = data.get("data") or {}
            items.extend(page.get(item_key) or [])
            if limit and len(items) >= limit:
                return items[:limit]
            if not page.get("has_more"):
                return items
            page_token = page.get("page_token") or ""
            if not page_token:
                return items

    @staticmethod
    def request_json(method: str, path: str, token: str | None = None, query: dict | None = None, body: dict | None = None) -> dict:
        url = f"{FeishuClient.API_BASE}{path}"
        if query:
            url = f"{url}?{urlencode({key: value for key, value in query.items() if value not in (None, '')})}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Feishu API HTTP {exc.code}: {detail[:200]}") from exc
        except URLError as exc:
            raise ValueError(f"Feishu API connection failed: {exc.reason}") from exc
        code = payload.get("code", 0)
        if code != 0:
            raise ValueError(f"Feishu API error {code}: {payload.get('msg') or payload.get('message') or payload}")
        return payload

    @staticmethod
    def root_department_id(config: dict) -> str:
        return str(config.get("root_department_id") or "0")

    @staticmethod
    def configured_department_ids(config: dict) -> list[str]:
        raw = config.get("department_ids") or config.get("sync_department_ids")
        if raw is None:
            return []
        if isinstance(raw, list):
            values = raw
        else:
            values = re.split(r"[\s,，、;；]+", str(raw))
        return [str(value).strip() for value in values if str(value).strip()]

    @staticmethod
    def discover_child_departments(config: dict) -> bool:
        value = config.get("discover_child_departments", True)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def login_only(config: dict) -> bool:
        value = config.get("login_only", False)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def is_no_dept_authority(exc: Exception) -> bool:
        message = str(exc).lower()
        return "no dept authority" in message or '"code":40004' in message or "code 40004" in message

    @staticmethod
    def user_status(item: dict) -> str:
        status = item.get("status") or {}
        if status.get("is_frozen") or status.get("is_resigned"):
            return "disabled"
        return "active"

    @staticmethod
    def local_user_id(external_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]+", "-", str(external_id).upper()).strip("-")
        if len(safe) <= 57:
            return f"FEISHU-{safe}"
        digest = hashlib.sha1(str(external_id).encode("utf-8")).hexdigest()[:16].upper()
        return f"FEISHU-{digest}"
