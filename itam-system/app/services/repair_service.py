from datetime import datetime

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.repair import RepairRecord
from app.schemas.repair import RepairCreate, RepairFinish
from app.services.lifecycle_service import LifecycleService


class RepairService:
    @staticmethod
    def list_records(db: Session) -> list[dict]:
        rows = db.query(RepairRecord).order_by(RepairRecord.id.desc()).all()
        assets = {asset.asset_id: asset for asset in db.query(Asset).all()}
        return [RepairService.to_dict(row, assets.get(row.asset_id)) for row in rows]

    @staticmethod
    def create_record(db: Session, payload: RepairCreate) -> dict:
        asset = db.get(Asset, payload.asset_id)
        if not asset:
            raise ValueError("asset not found")
        record = RepairRecord(
            repair_no=RepairService.generate_repair_no(db),
            asset_id=payload.asset_id,
            repair_time=payload.repair_time,
            fault_reason=payload.fault_reason,
            repair_cost=payload.repair_cost,
            vendor=payload.vendor,
            operator=payload.operator,
            status="维修中",
            remark=payload.remark,
        )
        db.add(record)
        from_status = asset.status
        asset.status = "repair"
        LifecycleService.record(db, asset.asset_id, "REPAIR_CREATE", from_status, "repair", payload.operator)
        db.commit()
        db.refresh(record)
        db.refresh(asset)
        return RepairService.to_dict(record, asset)

    @staticmethod
    def finish_record(db: Session, record_id: int, payload: RepairFinish) -> dict:
        record = db.get(RepairRecord, record_id)
        if not record:
            raise ValueError("repair record not found")
        asset = db.get(Asset, record.asset_id)
        record.status = "已完成"
        record.finish_time = payload.finish_time or datetime.utcnow()
        if payload.remark:
            record.remark = payload.remark
        if asset:
            from_status = asset.status
            asset.status = payload.next_status
            LifecycleService.record(db, asset.asset_id, "REPAIR_FINISH", from_status, payload.next_status, payload.operator)
        db.commit()
        db.refresh(record)
        if asset:
            db.refresh(asset)
        return RepairService.to_dict(record, asset)

    @staticmethod
    def generate_repair_no(db: Session) -> str:
        year = datetime.utcnow().year
        count = db.query(RepairRecord).count() + 1
        return f"RP-{year}-{count:04d}"

    @staticmethod
    def to_dict(record: RepairRecord, asset: Asset | None = None) -> dict:
        return {
            "id": record.id,
            "repair_no": record.repair_no,
            "asset_id": record.asset_id,
            "repair_time": record.repair_time,
            "fault_reason": record.fault_reason,
            "repair_cost": record.repair_cost,
            "vendor": record.vendor,
            "operator": record.operator,
            "status": record.status,
            "finish_time": record.finish_time,
            "remark": record.remark,
            "created_at": record.created_at,
            "asset_name": asset.name if asset else None,
            "sn": asset.sn if asset else None,
            "category": asset.category if asset else None,
            "owner": asset.owner_user_id if asset else None,
            "dept": asset.dept_id if asset else None,
            "current_status": asset.status if asset else None,
        }
