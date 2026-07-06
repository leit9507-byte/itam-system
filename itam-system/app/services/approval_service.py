import json
import uuid
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.approval import ApprovalInstanceLog, ApprovalRule
from app.models.purchase import Purchase
from app.models.repair import RepairRecord
from app.models.scrap import ScrapRequest
from app.services.asset_service import AssetService
from app.services.audit_log_service import AuditLogService
from app.services.purchase_service import PurchaseService
from app.services.repair_service import RepairService
from app.services.scrap_service import ScrapService


DEFAULT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
DEFAULT_INSTANCE_URL = "https://open.feishu.cn/open-apis/approval/v4/instances"


class ApprovalService:
    @staticmethod
    def config_out(row: ApprovalRule) -> dict:
        return {
            "id": row.id,
            "flow_type": row.flow_type,
            "name": row.name,
            "enabled": row.enabled,
            "min_amount": row.min_amount,
            "max_amount": row.max_amount,
            "dept_id": row.dept_id,
            "provider": row.provider or "feishu",
            "approval_code": row.approval_code,
            "app_id": row.app_id,
            "app_secret": "",
            "app_secret_set": bool(row.app_secret),
            "tenant_access_token_url": row.tenant_access_token_url or DEFAULT_TOKEN_URL,
            "instance_create_url": row.instance_create_url or DEFAULT_INSTANCE_URL,
            "submitter_user_id": row.submitter_user_id,
            "submitter_open_id": row.submitter_open_id,
            "form_template": row.form_template,
            "callback_token": row.callback_token,
            "callback_encrypt_key_set": bool(row.callback_encrypt_key),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def apply_config_payload(row: ApprovalRule, payload, keep_secret: bool = False) -> None:
        data = payload.model_dump()
        secret = data.pop("app_secret", None)
        data["provider"] = data.get("provider") or "feishu"
        data["tenant_access_token_url"] = data.get("tenant_access_token_url") or DEFAULT_TOKEN_URL
        data["instance_create_url"] = data.get("instance_create_url") or DEFAULT_INSTANCE_URL
        data["level"] = 1
        data["require_all"] = False
        data["approver_role"] = None
        data["approver_user_id"] = None
        for key, value in data.items():
            setattr(row, key, value)
        if secret:
            row.app_secret = secret
        elif not keep_secret:
            row.app_secret = None

    @staticmethod
    def match_config(db: Session, flow_type: str, amount: float = 0, dept_id: str | None = None) -> ApprovalRule | None:
        query = db.query(ApprovalRule).filter(ApprovalRule.enabled.is_(True), ApprovalRule.flow_type == flow_type)
        query = query.filter(or_(ApprovalRule.min_amount.is_(None), ApprovalRule.min_amount <= amount))
        query = query.filter(or_(ApprovalRule.max_amount.is_(None), ApprovalRule.max_amount >= amount))
        if dept_id:
            query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == "", ApprovalRule.dept_id == dept_id))
        else:
            query = query.filter(or_(ApprovalRule.dept_id.is_(None), ApprovalRule.dept_id == ""))
        return query.order_by(ApprovalRule.dept_id.desc(), ApprovalRule.min_amount.desc(), ApprovalRule.id.asc()).first()

    @staticmethod
    def submit_feishu_approval(
        db: Session,
        flow_type: str,
        business_id: str | None = None,
        amount: float = 0,
        dept_id: str | None = None,
        user_id: str | None = None,
        open_id: str | None = None,
        form: list[dict] | dict | None = None,
        requester: str = "system",
    ) -> dict:
        config = ApprovalService.match_config(db, flow_type, amount, dept_id)
        if not config:
            raise ValueError("未找到启用的飞书审批配置")
        if (config.provider or "feishu") != "feishu":
            raise ValueError("当前配置不是飞书审批")
        if not config.app_id or not config.app_secret or not config.approval_code:
            raise ValueError("飞书审批配置缺少 app_id、app_secret 或 approval_code")

        submitter_user_id = user_id or config.submitter_user_id
        submitter_open_id = open_id or config.submitter_open_id
        if not submitter_user_id and not submitter_open_id:
            raise ValueError("飞书审批需要配置或传入 submitter_user_id/open_id")

        final_form = ApprovalService.build_form(config.form_template, form)
        request_payload = {
            "approval_code": config.approval_code,
            "user_id": submitter_user_id,
            "open_id": submitter_open_id,
            "form": json.dumps(final_form, ensure_ascii=False),
            "uuid": str(uuid.uuid4()),
        }
        request_payload = {key: value for key, value in request_payload.items() if value not in (None, "")}
        log = ApprovalInstanceLog(
            flow_type=flow_type,
            config_id=config.id,
            business_id=business_id,
            approval_code=config.approval_code,
            requester=requester,
            request_payload=json.dumps(request_payload, ensure_ascii=False),
            status="submitting",
        )
        db.add(log)
        db.flush()
        try:
            token = ApprovalService.fetch_tenant_access_token(config)
            response = ApprovalService.post_json(config.instance_create_url or DEFAULT_INSTANCE_URL, request_payload, {"Authorization": f"Bearer {token}"})
            log.response_payload = json.dumps(response, ensure_ascii=False)
            log.instance_code = ApprovalService.extract_instance_code(response)
            log.status = "submitted" if log.instance_code else "submitted_unknown"
            AuditLogService.record_operation(db, "approval", "feishu_submit", requester, "approval_instance", log.instance_code or str(log.id), f"{flow_type} 提交飞书审批", request_payload)
            db.commit()
            db.refresh(log)
            return {"config": config, "instance": log, "feishu": response}
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
            AuditLogService.record_operation(db, "approval", "feishu_submit_failed", requester, "approval_instance", str(log.id), f"{flow_type} 飞书审批提交失败", str(exc))
            db.commit()
            raise

    @staticmethod
    def handle_feishu_callback(db: Session, payload: dict, operator: str = "feishu-callback") -> dict:
        if payload.get("challenge"):
            return {"challenge": payload["challenge"]}
        event = payload.get("event") or payload.get("data") or payload
        instance_code = ApprovalService.first_value(event, ["instance_code", "approval_instance_code", "uuid"])
        approval_code = ApprovalService.first_value(event, ["approval_code"])
        raw_status = ApprovalService.first_value(event, ["status", "approval_status", "instance_status", "task_status"])
        status = ApprovalService.normalize_callback_status(raw_status)
        if not instance_code:
            raise ValueError("callback missing instance_code")

        log = db.query(ApprovalInstanceLog).filter(ApprovalInstanceLog.instance_code == instance_code).first()
        if not log and approval_code:
            log = (
                db.query(ApprovalInstanceLog)
                .filter(ApprovalInstanceLog.approval_code == approval_code)
                .order_by(ApprovalInstanceLog.id.desc())
                .first()
            )
        if not log:
            log = ApprovalInstanceLog(
                flow_type=event.get("flow_type") or "unknown",
                approval_code=approval_code,
                instance_code=instance_code,
                status="callback_unmatched",
            )
            db.add(log)
            db.flush()

        log.status = status
        log.response_payload = json.dumps(payload, ensure_ascii=False)
        log.updated_at = datetime.utcnow()
        result = {"status": status, "instance_code": instance_code, "business_id": log.business_id, "flow_type": log.flow_type}
        if status == "approved":
            result["business_result"] = ApprovalService.apply_business_approval(db, log, operator)
        elif status in {"rejected", "canceled"}:
            result["business_result"] = ApprovalService.apply_business_rejection(db, log, operator, status)
        AuditLogService.record_operation(db, "approval", "feishu_callback", operator, "approval_instance", instance_code, f"飞书审批回调 {status}", payload)
        db.commit()
        return result

    @staticmethod
    def apply_business_approval(db: Session, log: ApprovalInstanceLog, operator: str) -> dict:
        if log.flow_type == "scrap":
            request = ApprovalService.find_scrap_request(db, log.business_id)
            if request:
                ScrapService.approve(db, request.id, operator)
                return {"scrap_request": request.request_no, "status": "approved"}
        if log.flow_type == "purchase" and log.business_id:
            PurchaseService.approve_purchase(db, log.business_id, operator, allow_submitted=True)
            return {"purchase_no": log.business_id, "status": "pending_acceptance"}
        if log.flow_type == "repair":
            record = ApprovalService.find_repair_record(db, log.business_id)
            if record:
                RepairService.approve_record(db, record.id, operator)
                return {"repair_no": record.repair_no, "status": "repairing"}
        if log.flow_type == "reclaim" and log.business_id:
            AssetService.change_status(db, log.business_id, "in_stock", operator, remark="飞书审批通过，资产回收入库")
            return {"asset_id": log.business_id, "status": "in_stock"}
        return {"status": "no_business_action"}

    @staticmethod
    def apply_business_rejection(db: Session, log: ApprovalInstanceLog, operator: str, status: str) -> dict:
        if log.flow_type == "scrap":
            request = ApprovalService.find_scrap_request(db, log.business_id)
            if request:
                ScrapService.reject(db, request.id, operator)
                return {"scrap_request": request.request_no, "status": status}
        if log.flow_type == "purchase" and log.business_id:
            purchase = db.query(Purchase).filter(Purchase.purchase_no == log.business_id).first()
            if purchase:
                purchase.status = "rejected" if status == "rejected" else "created"
                return {"purchase_no": purchase.purchase_no, "status": purchase.status}
        if log.flow_type == "repair":
            record = ApprovalService.find_repair_record(db, log.business_id)
            if record:
                RepairService.reject_record(db, record.id, operator)
                return {"repair_no": record.repair_no, "status": "rejected"}
        return {"status": "no_business_action"}

    @staticmethod
    def build_form(template_text: str | None, submitted: list[dict] | dict | None) -> list[dict]:
        if submitted:
            return submitted if isinstance(submitted, list) else [{"id": key, "value": value} for key, value in submitted.items()]
        if not template_text:
            return []
        parsed = json.loads(template_text)
        return parsed if isinstance(parsed, list) else [{"id": key, "value": value} for key, value in parsed.items()]

    @staticmethod
    def fetch_tenant_access_token(config: ApprovalRule) -> str:
        response = ApprovalService.post_json(
            config.tenant_access_token_url or DEFAULT_TOKEN_URL,
            {"app_id": config.app_id, "app_secret": config.app_secret},
        )
        token = response.get("tenant_access_token") or response.get("data", {}).get("tenant_access_token")
        if not token:
            raise ValueError(response.get("msg") or "tenant_access_token missing")
        return token

    @staticmethod
    def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = UrlRequest(url, data=body, headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})}, method="POST")
        try:
            with urlopen(request, timeout=15) as response:
                data = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ValueError(str(exc.reason)) from exc
        result = json.loads(data or "{}")
        code = result.get("code", 0)
        if code not in (0, None):
            raise ValueError(result.get("msg") or data)
        return result

    @staticmethod
    def instance_out(row: ApprovalInstanceLog) -> dict:
        return {
            "id": row.id,
            "flow_type": row.flow_type,
            "config_id": row.config_id,
            "business_id": row.business_id,
            "approval_code": row.approval_code,
            "instance_code": row.instance_code,
            "status": row.status,
            "requester": row.requester,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def extract_instance_code(response: dict) -> str | None:
        data = response.get("data") or {}
        return data.get("instance_code") or response.get("instance_code")

    @staticmethod
    def normalize_callback_status(value: Any) -> str:
        text = str(value or "").lower()
        if text in {"approved", "approve", "pass", "passed", "success"} or "approved" in text:
            return "approved"
        if text in {"rejected", "reject", "refused", "failed"} or "reject" in text:
            return "rejected"
        if text in {"canceled", "cancelled", "cancel", "withdraw", "withdrawn"} or "cancel" in text or "withdraw" in text:
            return "canceled"
        return text or "unknown"

    @staticmethod
    def first_value(data: dict, keys: list[str]) -> Any:
        for key in keys:
            if key in data:
                return data[key]
        for value in data.values():
            if isinstance(value, dict):
                nested = ApprovalService.first_value(value, keys)
                if nested is not None:
                    return nested
        return None

    @staticmethod
    def find_scrap_request(db: Session, business_id: str | None) -> ScrapRequest | None:
        if not business_id:
            return None
        query = db.query(ScrapRequest)
        if str(business_id).isdigit():
            row = query.filter(ScrapRequest.id == int(business_id)).first()
            if row:
                return row
        return query.filter(ScrapRequest.request_no == business_id).first()

    @staticmethod
    def find_repair_record(db: Session, business_id: str | None) -> RepairRecord | None:
        if not business_id:
            return None
        query = db.query(RepairRecord)
        if str(business_id).isdigit():
            row = query.filter(RepairRecord.id == int(business_id)).first()
            if row:
                return row
        return query.filter(RepairRecord.repair_no == business_id).first()
