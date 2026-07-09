import json

from sqlalchemy.orm import Session

from app.models.lifecycle import Lifecycle


class LifecycleService:
    @staticmethod
    def record(
        db: Session,
        asset_id: str,
        action_type: str,
        from_status: str | None,
        to_status: str | None,
        operator: str = "system",
        remark: str | dict | None = None,
    ) -> Lifecycle:
        lifecycle = Lifecycle(
            asset_id=asset_id,
            action_type=action_type,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            remark=LifecycleService.serialize_remark(remark),
        )
        db.add(lifecycle)
        return lifecycle

    @staticmethod
    def structured_remark(
        *,
        reason: str | None = None,
        object: str | None = None,
        previous_owner: str | None = None,
        new_owner: str | None = None,
        location: str | None = None,
        due_date: str | None = None,
        extra: dict | None = None,
    ) -> dict:
        return {
            "format": "itam.lifecycle.v1",
            "reason": reason or "",
            "object": object or "",
            "previous_owner": previous_owner or "",
            "new_owner": new_owner or "",
            "location": location or "",
            "due_date": due_date or "",
            "extra": extra or {},
        }

    @staticmethod
    def serialize_remark(remark: str | dict | None) -> str | None:
        if remark is None:
            return None
        if isinstance(remark, dict):
            return json.dumps(remark, ensure_ascii=False, separators=(",", ":"))
        return remark
