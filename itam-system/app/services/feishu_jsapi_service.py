import hashlib
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy.orm import Session

from app.models.user import IdentityProviderConfig


DEFAULT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
DEFAULT_JSAPI_TICKET_URL = "https://open.feishu.cn/open-apis/jssdk/ticket/get"
TICKET_REFRESH_SKEW_SECONDS = 300


class FeishuJsapiService:
    _ticket_cache: dict[str, tuple[str, float]] = {}

    @staticmethod
    def clear_cache(app_id: str | None = None) -> None:
        if app_id:
            FeishuJsapiService._ticket_cache.pop(app_id, None)
            return
        FeishuJsapiService._ticket_cache.clear()

    @staticmethod
    def build_signature(db: Session, url: str) -> dict:
        clean_url = FeishuJsapiService.clean_url(url)
        app_id, app_secret = FeishuJsapiService.find_credentials(db)
        ticket = FeishuJsapiService.get_cached_jsapi_ticket(app_id, app_secret)
        timestamp = int(time.time() * 1000)
        nonce_str = secrets.token_hex(12)
        raw = f"jsapi_ticket={ticket}&noncestr={nonce_str}&timestamp={timestamp}&url={clean_url}"
        signature = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return {
            "appId": app_id,
            "timestamp": timestamp,
            "nonceStr": nonce_str,
            "signature": signature,
            "url": clean_url,
            "jsApiList": ["scanCode"],
            "expiresIn": 600,
        }

    @staticmethod
    def clean_url(url: str) -> str:
        clean, _ = urldefrag((url or "").strip())
        if not clean.startswith(("https://", "http://")):
            raise ValueError("url must be absolute")
        return clean

    @staticmethod
    def find_credentials(db: Session) -> tuple[str, str]:
        provider = (
            db.query(IdentityProviderConfig)
            .filter(IdentityProviderConfig.provider_type == "feishu", IdentityProviderConfig.enabled.is_(True))
            .order_by(IdentityProviderConfig.id.asc())
            .first()
        )
        if provider:
            config = provider.config or {}
            app_id = config.get("app_id")
            app_secret = config.get("app_secret")
            if app_id and app_secret:
                return app_id, app_secret

        raise ValueError("未配置启用的飞书 App ID/App Secret")

    @staticmethod
    def get_cached_jsapi_ticket(app_id: str, app_secret: str) -> str:
        cached = FeishuJsapiService._ticket_cache.get(app_id)
        now = time.time()
        if cached and cached[1] > now:
            return cached[0]

        token = FeishuJsapiService.fetch_tenant_access_token(app_id, app_secret)
        ticket, expires_in = FeishuJsapiService.fetch_jsapi_ticket(token)
        ttl = max(int(expires_in or 7200) - TICKET_REFRESH_SKEW_SECONDS, 60)
        FeishuJsapiService._ticket_cache[app_id] = (ticket, now + ttl)
        return ticket

    @staticmethod
    def fetch_tenant_access_token(app_id: str, app_secret: str) -> str:
        body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        request = UrlRequest(DEFAULT_TOKEN_URL, data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        try:
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"tenant token fetch failed: HTTP {exc.code} {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError(f"tenant token fetch failed: {exc}") from exc
        code = result.get("code", 0)
        if code not in (0, None):
            raise ValueError(result.get("msg") or "tenant token fetch failed")
        token = result.get("tenant_access_token") or (result.get("data") or {}).get("tenant_access_token")
        if not token:
            raise ValueError("tenant_access_token missing")
        return token

    @staticmethod
    def fetch_jsapi_ticket(tenant_access_token: str) -> tuple[str, int]:
        request = UrlRequest(
            DEFAULT_JSAPI_TICKET_URL,
            data=b"{}",
            headers={
                "Authorization": f"Bearer {tenant_access_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"jsapi ticket fetch failed: HTTP {exc.code} {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError(f"jsapi ticket fetch failed: {exc}") from exc
        code = result.get("code", 0)
        if code not in (0, None):
            raise ValueError(result.get("msg") or "jsapi ticket fetch failed")
        data = result.get("data") or {}
        ticket = data.get("ticket") or result.get("ticket")
        if not ticket:
            raise ValueError("jsapi ticket missing")
        expires_in = data.get("expire_in") or data.get("expires_in") or result.get("expire_in") or result.get("expires_in") or 7200
        return ticket, int(expires_in)
