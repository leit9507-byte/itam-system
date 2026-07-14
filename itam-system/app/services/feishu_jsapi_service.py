import hashlib
import json
import secrets
import time
from urllib.parse import urldefrag
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy.orm import Session

from app.models.approval import ApprovalRule
from app.models.user import IdentityProviderConfig
from app.services.approval_service import ApprovalService


DEFAULT_JSAPI_TICKET_URL = "https://open.feishu.cn/open-apis/jssdk/ticket/get"


class FeishuJsapiService:
    @staticmethod
    def build_signature(db: Session, url: str) -> dict:
        clean_url = FeishuJsapiService.clean_url(url)
        app_id, app_secret = FeishuJsapiService.find_credentials(db)
        token = ApprovalService.fetch_tenant_access_token(
            type(
                "FeishuTokenConfig",
                (),
                {
                    "app_id": app_id,
                    "app_secret": app_secret,
                    "tenant_access_token_url": None,
                },
            )()
        )
        ticket = FeishuJsapiService.fetch_jsapi_ticket(token)
        timestamp = str(int(time.time() * 1000))
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

        rule = (
            db.query(ApprovalRule)
            .filter(ApprovalRule.provider == "feishu", ApprovalRule.enabled.is_(True), ApprovalRule.app_id.isnot(None), ApprovalRule.app_secret.isnot(None))
            .order_by(ApprovalRule.id.asc())
            .first()
        )
        if rule and rule.app_id and rule.app_secret:
            return rule.app_id, rule.app_secret

        raise ValueError("未配置启用的飞书 App ID/App Secret")

    @staticmethod
    def fetch_jsapi_ticket(tenant_access_token: str) -> str:
        request = UrlRequest(DEFAULT_JSAPI_TICKET_URL, headers={"Authorization": f"Bearer {tenant_access_token}"}, method="GET")
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
        code = result.get("code", 0)
        if code not in (0, None):
            raise ValueError(result.get("msg") or "jsapi ticket fetch failed")
        ticket = result.get("data", {}).get("ticket") or result.get("ticket")
        if not ticket:
            raise ValueError("jsapi ticket missing")
        return ticket
