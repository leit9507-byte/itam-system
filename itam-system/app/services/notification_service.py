import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.notification import NotificationSetting
from app.schemas.notification import NotificationSettingSave


class NotificationService:
    CHANNEL = "feishu_webhook"
    DEFAULT_EVENT_TYPES = {
        "inbound": True,
        "outbound": True,
        "stocktake": True,
        "risk": True,
    }
    EVENT_LABELS = {
        "inbound": "入库通知",
        "outbound": "出库通知",
        "stocktake": "盘点通知",
        "risk": "风险通知",
    }

    @staticmethod
    def get_setting(db: Session) -> NotificationSetting:
        setting = db.query(NotificationSetting).filter(NotificationSetting.channel == NotificationService.CHANNEL).first()
        if setting:
            NotificationService.ensure_event_types(setting)
            return setting
        setting = NotificationSetting(channel=NotificationService.CHANNEL, enabled=False, event_types=NotificationService.DEFAULT_EVENT_TYPES.copy())
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def save_setting(db: Session, payload: NotificationSettingSave) -> NotificationSetting:
        NotificationService.validate_webhook_url(payload.webhook_url)
        setting = NotificationService.get_setting(db)
        setting.enabled = payload.enabled
        setting.webhook_url = (payload.webhook_url or "").strip() or None
        setting.secret = (payload.secret or "").strip() or None
        setting.event_types = NotificationService.normalize_event_types(payload.event_types)
        setting.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def send_event(db: Session, event_type: str, title: str, lines: list[str] | None = None) -> bool:
        setting = NotificationService.get_setting(db)
        if not NotificationService.event_enabled(setting, event_type):
            return False
        if not setting.webhook_url:
            return False

        try:
            NotificationService.send_message_with_setting(setting, NotificationService.format_event_message(event_type, title, lines))
            return True
        except Exception as exc:
            setting.last_test_status = "failed"
            setting.last_test_message = str(exc)[:255]
            db.commit()
            return False

    @staticmethod
    def preview_messages() -> list[dict]:
        samples = {
            "inbound": {
                "title": "资产入库完成",
                "lines": [
                    "资产名称：ThinkPad X1 Carbon",
                    "资产编号：ITAM-002356",
                    "状态变更：在用 -> 在库",
                    "入库位置：上海IT仓",
                    "原责任人：张三（U-ZHANGSAN）",
                    "操作人：ITAM Admin（admin）",
                    "操作时间：2026-07-02 19:20:00",
                ],
            },
            "outbound": {
                "title": "资产出库完成",
                "lines": [
                    "资产名称：Dell U2723QE 显示器",
                    "资产编号：ITAM-002357",
                    "状态变更：在库 -> 在用",
                    "领用人：张三（U-ZHANGSAN）",
                    "所属部门：研发中心",
                    "使用位置：上海办公区 A-08",
                    "操作人：ITAM Admin（admin）",
                    "操作时间：2026-07-02 19:20:00",
                ],
            },
            "stocktake": {
                "title": "盘点任务已开始",
                "lines": [
                    "任务名称：月度资产盘点",
                    "任务编号：ST-2026-001",
                    "盘点范围：部门 / 研发中心",
                    "应盘资产：128 台",
                    "负责人：资产管理员",
                    "开始时间：2026-07-02 19:20:00",
                ],
            },
            "risk": {
                "title": "审计发现风险",
                "lines": [
                    "风险总数：6 条",
                    "风险评分：75",
                    "人员风险：2 条",
                    "资产风险：4 条",
                    "高风险：1 条",
                    "处理建议：请进入审计中心查看明细并分派整改",
                    "审计时间：2026-07-02 19:20:00",
                ],
            },
        }
        return [
            {
                "event_type": key,
                "label": NotificationService.EVENT_LABELS.get(key, key),
                "message": NotificationService.format_event_message(key, item["title"], item["lines"]),
            }
            for key, item in samples.items()
        ]

    @staticmethod
    def format_event_message(event_type: str, title: str, lines: list[str] | None = None) -> str:
        label = NotificationService.EVENT_LABELS.get(event_type, "系统通知")
        body_lines = [f"【{label}】", title, *[line for line in (lines or []) if line]]
        return "\n".join(body_lines)

    @staticmethod
    def send_test(db: Session, message: str) -> NotificationSetting:
        setting = NotificationService.get_setting(db)
        if not setting.webhook_url:
            raise ValueError("请填写飞书 Webhook 地址")
        NotificationService.validate_webhook_url(setting.webhook_url)

        text = message.strip() or "资产管理系统消息通知测试"
        try:
            NotificationService.send_message_with_setting(setting, text)
            setting.last_test_status = "success"
            setting.last_test_message = f"已发送：{text}"[:255]
        except Exception as exc:
            setting.last_test_status = "failed"
            setting.last_test_message = str(exc)[:255]
            db.commit()
            db.refresh(setting)
            raise ValueError(setting.last_test_message) from exc

        setting.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def ensure_event_types(setting: NotificationSetting) -> None:
        setting.event_types = NotificationService.normalize_event_types(setting.event_types or {})

    @staticmethod
    def normalize_event_types(values: dict | None) -> dict[str, bool]:
        values = values or {}
        return {key: bool(values.get(key, default)) for key, default in NotificationService.DEFAULT_EVENT_TYPES.items()}

    @staticmethod
    def event_enabled(setting: NotificationSetting, event_type: str) -> bool:
        if not setting.enabled:
            return False
        event_types = NotificationService.normalize_event_types(setting.event_types or {})
        return bool(event_types.get(event_type))

    @staticmethod
    def validate_webhook_url(url: str | None) -> None:
        if not url:
            return
        parsed = urlparse(url.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("webhook_url must be a valid https URL")
        host = parsed.netloc.lower()
        if not (host.endswith("feishu.cn") or host.endswith("larksuite.com")):
            raise ValueError("webhook_url must be a Feishu/Lark webhook URL")

    @staticmethod
    def build_feishu_sign(timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def send_message_with_setting(setting: NotificationSetting, text: str) -> None:
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        if setting.secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = NotificationService.build_feishu_sign(timestamp, setting.secret)
        result = NotificationService.post_json(setting.webhook_url, payload)
        status_code = result.get("StatusCode") or result.get("code")
        status_message = result.get("StatusMessage") or result.get("msg") or "sent"
        if status_code not in (0, "0", None):
            raise ValueError(f"Feishu returned {status_code}: {status_message}")

    @staticmethod
    def post_json(url: str, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Feishu HTTP {exc.code}: {raw[:200]}") from exc
        if not raw:
            return {}
        return json.loads(raw)
