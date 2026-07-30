import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AssetChangeLog, OperationAuditLog


class AuditLogService:
    @staticmethod
    def serialize(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)

    @staticmethod
    def record_asset_change(
        db: Session,
        asset_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        operator: str,
        field_label: str | None = None,
        source: str = "asset_update",
    ) -> None:
        old_text = AuditLogService.serialize(old_value)
        new_text = AuditLogService.serialize(new_value)
        if old_text == new_text:
            return
        db.add(
            AssetChangeLog(
                asset_id=asset_id,
                field_name=field_name,
                field_label=field_label or field_name,
                old_value=old_text,
                new_value=new_text,
                operator=operator or "system",
                source=source,
            )
        )

    @staticmethod
    def record_operation(
        db: Session,
        module: str,
        action: str,
        operator: str,
        target_type: str | None = None,
        target_id: str | None = None,
        summary: str | None = None,
        detail: Any = None,
    ) -> None:
        db.add(
            OperationAuditLog(
                module=module,
                action=action,
                target_type=target_type,
                target_id=target_id,
                operator=operator or "system",
                summary=summary,
                detail=AuditLogService.serialize(detail) if detail is not None else None,
            )
        )
        from app.services.dashboard_service import DashboardService

        DashboardService.invalidate()
