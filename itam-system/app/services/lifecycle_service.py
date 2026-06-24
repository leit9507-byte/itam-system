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
        remark: str | None = None,
    ) -> Lifecycle:
        lifecycle = Lifecycle(
            asset_id=asset_id,
            action_type=action_type,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            remark=remark,
        )
        db.add(lifecycle)
        return lifecycle
