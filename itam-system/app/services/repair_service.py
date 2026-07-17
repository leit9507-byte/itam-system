from datetime import datetime

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core.security import can_view_all_data, is_department_manager, scoped_dept_id, scoped_user_identities
from app.models.asset import Asset
from app.models.repair import RepairFaultType, RepairRecord
from app.schemas.repair import RepairCreate, RepairFinish
from app.services.audit_log_service import AuditLogService
from app.services.lifecycle_service import LifecycleService
from app.services.notification_service import NotificationService


class RepairService:
    default_fault_types = ["无法开机", "屏幕损坏", "电池故障", "主板故障", "网络异常", "系统故障", "外壳/结构损坏"]

    @staticmethod
    def ensure_fault_types(db: Session) -> None:
        if db.query(RepairFaultType).first():
            return
        for name in RepairService.default_fault_types:
            db.add(RepairFaultType(name=name, description="", enabled="启用"))
        db.commit()

    @staticmethod
    def list_fault_types(db: Session) -> list[RepairFaultType]:
        RepairService.ensure_fault_types(db)
        return db.query(RepairFaultType).order_by(RepairFaultType.enabled.desc(), RepairFaultType.id.asc()).all()

    @staticmethod
    def save_fault_type(db: Session, payload, fault_type_id: int | None = None) -> RepairFaultType:
        RepairService.ensure_fault_types(db)
        name = payload.name.strip()
        if not name:
            raise ValueError("fault type name is required")
        row = db.get(RepairFaultType, fault_type_id) if fault_type_id else None
        existed = db.query(RepairFaultType).filter(RepairFaultType.name == name).first()
        if existed and (not row or existed.id != row.id):
            raise ValueError("fault type already exists")
        if not row:
            row = RepairFaultType()
            db.add(row)
        row.name = name
        row.description = payload.description or ""
        row.enabled = payload.enabled or "启用"
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_fault_type(db: Session, fault_type_id: int) -> None:
        row = db.get(RepairFaultType, fault_type_id)
        if not row:
            raise ValueError("fault type not found")
        db.delete(row)
        db.commit()

    @staticmethod
    def list_records(
        db: Session,
        page: int = 1,
        page_size: int = 0,
        keyword: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_context: dict | None = None,
    ) -> dict:
        query = db.query(RepairRecord).outerjoin(Asset, Asset.asset_id == RepairRecord.asset_id)
        query = RepairService.apply_data_scope(query, user_context)
        if status:
            query = query.filter(RepairRecord.status == status)
        if start_date:
            query = query.filter(RepairRecord.repair_time >= start_date)
        if end_date:
            query = query.filter(RepairRecord.repair_time <= end_date)
        clean_keyword = (keyword or "").strip()
        if clean_keyword:
            pattern = f"%{clean_keyword}%"
            query = query.filter(
                or_(
                    RepairRecord.asset_id.like(pattern),
                    RepairRecord.repair_no.like(pattern),
                    RepairRecord.fault_reason.like(pattern),
                    RepairRecord.vendor.like(pattern),
                    Asset.name.like(pattern),
                    Asset.sn.like(pattern),
                )
            )
        total = query.count()
        count_subquery = query.with_entities(
            RepairRecord.asset_id.label("asset_id"),
            func.count(RepairRecord.id).label("fault_device_count"),
        ).group_by(RepairRecord.asset_id).subquery()
        if sort_by == "fault_device_count":
            count_column = count_subquery.c.fault_device_count
            query = query.join(count_subquery, count_subquery.c.asset_id == RepairRecord.asset_id)
            query = query.order_by(count_column.asc() if sort_order == "asc" else desc(count_column), RepairRecord.id.desc())
        else:
            query = query.order_by(RepairRecord.id.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        rows = query.all()
        asset_ids = [row.asset_id for row in rows]
        assets = {asset.asset_id: asset for asset in db.query(Asset).filter(Asset.asset_id.in_(asset_ids)).all()} if asset_ids else {}
        repair_counts = {
            row.asset_id: int(row.fault_device_count or 0)
            for row in db.query(count_subquery).filter(count_subquery.c.asset_id.in_(asset_ids)).all()
        } if asset_ids else {}
        return {"list": [RepairService.to_dict(row, assets.get(row.asset_id), repair_counts.get(row.asset_id, 1)) for row in rows], "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def apply_data_scope(query, user_context: dict | None):
        if can_view_all_data(user_context):
            return query
        dept_id = scoped_dept_id(user_context)
        identities = scoped_user_identities(user_context)
        if is_department_manager(user_context) and dept_id:
            return query.filter(Asset.dept_id == dept_id)
        if identities:
            return query.filter(Asset.owner_user_id.in_(identities))
        return query.filter(False)

    @staticmethod
    def create_record(db: Session, payload: RepairCreate, start_work: bool = True) -> dict:
        asset = db.get(Asset, payload.asset_id)
        if not asset:
            raise ValueError("asset not found")
        if asset.status in {"scrapped", "disposed"}:
            raise ValueError("已报废/已处置资产不能创建维修单")
        record = RepairRecord(
            repair_no=RepairService.generate_repair_no(db),
            asset_id=payload.asset_id,
            repair_time=payload.repair_time,
            repair_type=payload.repair_type or "普通维修",
            fault_reason=payload.fault_reason,
            repair_cost=payload.repair_cost,
            vendor=payload.vendor,
            operator=payload.operator,
            status="维修中" if start_work else "approval_submitted",
            remark=payload.remark,
        )
        db.add(record)
        if start_work:
            from_status = asset.status
            asset.status = "repair"
            LifecycleService.record(db, asset.asset_id, "REPAIR_CREATE", from_status, "repair", payload.operator)
        else:
            LifecycleService.record(db, asset.asset_id, "REPAIR_APPROVAL_SUBMIT", asset.status, asset.status, payload.operator)
        AuditLogService.record_operation(db, "repair", "create" if start_work else "approval_submit", payload.operator, "repair", record.repair_no, f"维修{'创建' if start_work else '提交飞书审批'} {record.asset_id}", payload.model_dump())
        db.commit()
        db.refresh(record)
        db.refresh(asset)
        NotificationService.send_event(
            db,
            "repair",
            "维修任务已创建" if start_work else "维修审批已提交",
            [
                f"维修单号：{record.repair_no}",
                f"资产编号：{record.asset_id}",
                f"资产名称：{asset.name or '-'}",
                f"维修类型：{record.repair_type or '-'}",
                f"故障类型：{record.fault_reason or '-'}",
                f"维修供应商：{record.vendor or '-'}",
                f"操作人：{payload.operator}",
            ],
        )
        return RepairService.to_dict(record, asset)

    @staticmethod
    def approve_record(db: Session, record_id: int, operator: str = "system") -> dict:
        record = db.get(RepairRecord, record_id)
        if not record:
            raise ValueError("repair record not found")
        asset = db.get(Asset, record.asset_id)
        record.status = "维修中"
        if asset:
            if asset.status in {"scrapped", "disposed"}:
                raise ValueError("已报废/已处置资产不能进入维修")
            from_status = asset.status
            asset.status = "repair"
            LifecycleService.record(db, asset.asset_id, "REPAIR_APPROVE", from_status, "repair", operator)
        AuditLogService.record_operation(db, "repair", "approve", operator, "repair", record.repair_no, f"维修审批通过 {record.asset_id}")
        db.commit()
        db.refresh(record)
        if asset:
            db.refresh(asset)
        NotificationService.send_event(
            db,
            "repair",
            "维修审批已通过",
            [
                f"维修单号：{record.repair_no}",
                f"资产编号：{record.asset_id}",
                f"当前状态：维修中",
                f"审批人：{operator}",
            ],
        )
        return RepairService.to_dict(record, asset)

    @staticmethod
    def reject_record(db: Session, record_id: int, operator: str = "system") -> dict:
        record = db.get(RepairRecord, record_id)
        if not record:
            raise ValueError("repair record not found")
        asset = db.get(Asset, record.asset_id)
        record.status = "rejected"
        if asset:
            LifecycleService.record(db, asset.asset_id, "REPAIR_REJECT", asset.status, asset.status, operator)
        AuditLogService.record_operation(db, "repair", "reject", operator, "repair", record.repair_no, f"维修审批驳回 {record.asset_id}")
        db.commit()
        db.refresh(record)
        NotificationService.send_event(
            db,
            "repair",
            "维修审批已驳回",
            [
                f"维修单号：{record.repair_no}",
                f"资产编号：{record.asset_id}",
                f"审批人：{operator}",
                f"当前状态：已驳回",
            ],
        )
        return RepairService.to_dict(record, asset)

    @staticmethod
    def finish_record(db: Session, record_id: int, payload: RepairFinish) -> dict:
        record = db.get(RepairRecord, record_id)
        if not record:
            raise ValueError("repair record not found")
        asset = db.get(Asset, record.asset_id)
        record.status = "已完成"
        record.repair_result = payload.repair_result or "已修好"
        if record.repair_result == "未修好":
            record.status = "未修好"
        elif record.repair_result == "在保送修":
            record.status = "在保送修"
        record.finish_time = payload.finish_time or datetime.utcnow()
        if payload.remark:
            record.remark = payload.remark
        if asset:
            if asset.status in {"scrapped", "disposed"}:
                raise ValueError("已报废/已处置资产不能变更维修状态")
            from_status = asset.status
            asset.status = payload.next_status
            LifecycleService.record(db, asset.asset_id, "REPAIR_FINISH", from_status, payload.next_status, payload.operator)
        AuditLogService.record_operation(db, "repair", "finish", payload.operator, "repair", record.repair_no, f"维修处理 {record.asset_id}：{record.repair_result}", payload.model_dump())
        db.commit()
        db.refresh(record)
        if asset:
            db.refresh(asset)
        NotificationService.send_event(
            db,
            "repair",
            f"维修任务已处理：{record.repair_result}",
            [
                f"维修单号：{record.repair_no}",
                f"资产编号：{record.asset_id}",
                f"资产名称：{asset.name if asset else '-'}",
                f"维修类型：{record.repair_type or '-'}",
                f"维修结果：{record.repair_result or '-'}",
                f"后续状态：{payload.next_status}",
                f"操作人：{payload.operator}",
            ],
        )
        return RepairService.to_dict(record, asset)

    @staticmethod
    def generate_repair_no(db: Session) -> str:
        year = datetime.utcnow().year
        count = db.query(RepairRecord).count() + 1
        return f"RP-{year}-{count:04d}"

    @staticmethod
    def to_dict(record: RepairRecord, asset: Asset | None = None, fault_device_count: int = 1) -> dict:
        return {
            "id": record.id,
            "repair_no": record.repair_no,
            "asset_id": record.asset_id,
            "repair_time": record.repair_time,
            "repair_type": record.repair_type,
            "fault_reason": record.fault_reason,
            "repair_cost": record.repair_cost,
            "vendor": record.vendor,
            "operator": record.operator,
            "status": record.status,
            "repair_result": record.repair_result,
            "fault_device_count": fault_device_count,
            "finish_time": record.finish_time,
            "remark": record.remark,
            "created_at": record.created_at,
            "asset_name": asset.name if asset else None,
            "sn": asset.sn if asset else None,
            "category": asset.category if asset else None,
            "brand": asset.brand if asset else None,
            "asset_model": asset.model if asset else None,
            "purchase_date": asset.purchase_date if asset else None,
            "owner": asset.owner_user_id if asset else None,
            "dept": asset.dept_id if asset else None,
            "current_status": asset.status if asset else None,
        }
