import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import UserDirectory
from app.schemas.asset import AssetBatchImport, AssetCreate, AssetImportRow, AssetTextImport, AssetUpdate
from app.services.lifecycle_service import LifecycleService


class AssetService:
    @staticmethod
    def generate_asset_id(db: Session, prefix: str = "ITAM") -> str:
        count = db.query(Asset).count() + 1
        return f"{prefix}-{count:06d}"

    @staticmethod
    def create_asset(db: Session, payload: AssetCreate, operator: str = "system") -> Asset:
        user = AssetService.find_user(db, payload.owner_user_id)
        asset = Asset(
            asset_id=getattr(payload, "asset_id", None) or AssetService.generate_asset_id(db),
            name=payload.name,
            category=payload.category,
            brand=payload.brand,
            model=payload.model,
            sn=payload.sn,
            config=payload.config,
            purchase_price=payload.purchase_price,
            purchase_date=payload.purchase_date,
            purchase_approval_no=payload.purchase_approval_no,
            purchase_supplier_name=payload.purchase_supplier_name,
            warranty_expire_date=payload.warranty_expire_date,
            warranty_months=payload.warranty_months,
            status=payload.status,
            owner_user_id=user.user_id if user else payload.owner_user_id,
            dept_id=(user.dept_id or user.dept_name) if user else payload.dept_id,
            location=payload.location,
        )
        db.add(asset)
        db.flush()
        LifecycleService.record(db, asset.asset_id, "CREATE", None, asset.status, operator)
        db.commit()
        db.refresh(asset)
        return AssetService.to_out(asset, user)

    @staticmethod
    def import_assets(db: Session, payload: AssetBatchImport) -> dict:
        created_assets: list[Asset] = []
        errors: list[dict] = []
        skipped = 0

        for index, row in enumerate(payload.items, start=1):
            try:
                normalized = AssetService.normalize_import_row(row)
                if normalized.sn and db.query(Asset).filter(Asset.sn == normalized.sn).first():
                    skipped += 1
                    errors.append({"row": index, "message": f"duplicate sn: {normalized.sn}", "data": row.model_dump()})
                    continue
                if normalized.asset_id and db.get(Asset, normalized.asset_id):
                    skipped += 1
                    errors.append({"row": index, "message": f"duplicate asset_id: {normalized.asset_id}", "data": row.model_dump()})
                    continue

                asset = Asset(
                    asset_id=normalized.asset_id or AssetService.generate_asset_id(db),
                    name=normalized.name,
                    category=normalized.category,
                    brand=normalized.brand,
                    model=normalized.model,
                    sn=normalized.sn,
                    config=normalized.config,
                    purchase_price=normalized.purchase_price,
                    purchase_date=normalized.purchase_date,
                    purchase_approval_no=normalized.purchase_approval_no,
                    purchase_supplier_name=normalized.purchase_supplier_name,
                    warranty_expire_date=normalized.warranty_expire_date,
                    warranty_months=normalized.warranty_months,
                    status=normalized.status,
                    owner_user_id=normalized.owner_user_id,
                    dept_id=normalized.dept_id,
                    location=normalized.location,
                )
                AssetService.sync_owner_department(db, asset)
                db.add(asset)
                db.flush()
                LifecycleService.record(db, asset.asset_id, "BATCH_IMPORT", None, asset.status, payload.operator)
                created_assets.append(asset)
            except Exception as exc:
                errors.append({"row": index, "message": str(exc), "data": row.model_dump()})

        db.commit()
        for asset in created_assets:
            db.refresh(asset)

        return {
            "created": len(created_assets),
            "skipped": skipped,
            "errors": errors,
            "assets": [AssetService.to_out(asset) for asset in created_assets],
        }

    @staticmethod
    def import_assets_from_text(db: Session, payload: AssetTextImport) -> dict:
        items = AssetService.parse_import_text(payload.content)
        return AssetService.import_assets(db, AssetBatchImport(operator=payload.operator, items=items))

    @staticmethod
    def import_assets_from_excel(db: Session, content: bytes, operator: str = "asset-import") -> dict:
        items = AssetService.parse_import_excel(content)
        return AssetService.import_assets(db, AssetBatchImport(operator=operator, items=items))

    @staticmethod
    def parse_import_text(content: str) -> list[AssetImportRow]:
        cleaned = content.strip()
        if not cleaned:
            return []
        delimiter = "\t" if "\t" in cleaned.splitlines()[0] else ","
        reader = csv.DictReader(StringIO(cleaned), delimiter=delimiter)
        return [AssetService.row_from_mapping(row) for row in reader if any(row.values())]

    @staticmethod
    def parse_import_excel(content: bytes) -> list[AssetImportRow]:
        workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        items: list[AssetImportRow] = []
        for values in rows[1:]:
            mapping = {
                headers[index]: value
                for index, value in enumerate(values)
                if index < len(headers) and headers[index] and value not in (None, "")
            }
            if mapping:
                items.append(AssetService.row_from_mapping(mapping))
        return items

    @staticmethod
    def row_from_mapping(row: dict[str, Any]) -> AssetImportRow:
        normalized_row = {str(key).strip(): value for key, value in row.items()}

        def pick(*keys: str, default=None):
            for key in keys:
                value = normalized_row.get(key)
                if value not in (None, ""):
                    return value
            return default

        price = pick("purchase_price", "price", "unit_price", "采购价格", "价格", "单价", default=0)
        config = {
            "spec": pick("spec", "规格", "配置", default=""),
            "warehouse": pick("warehouse", "仓库", default=""),
            "source": "batch_import",
        }
        return AssetImportRow(
            asset_id=pick("asset_id", "资产编号", "资产ID"),
            name=pick("name", "product_name", "产品名称", "资产名称", default="Unnamed Asset"),
            category=pick("category", "device_type", "设备类型", "类别", default="Other"),
            brand=pick("brand", "品牌"),
            model=pick("model", "型号"),
            sn=pick("sn", "serial_number", "序列号", "SN"),
            config=config,
            purchase_price=float(price or 0),
            purchase_date=AssetService.parse_datetime(pick("purchase_date", "采购日期", "采购时间")),
            purchase_approval_no=pick("purchase_approval_no", "采购审批单号", "审批单号", "采购单号"),
            purchase_supplier_name=pick("purchase_supplier_name", "采购供应商", "供应商"),
            warranty_expire_date=AssetService.parse_datetime(pick("warranty_expire_date", "质保到期", "质保到期日")),
            warranty_months=AssetService.parse_int(pick("warranty_months", "质保月数", "质保")),
            status=pick("status", "状态", default="in_stock"),
            owner_user_id=pick("owner_user_id", "owner", "使用人", "责任人"),
            dept_id=pick("dept_id", "dept", "部门"),
            location=pick("location", "warehouse", "位置", "仓库"),
        )

    @staticmethod
    def normalize_import_row(row: AssetImportRow) -> AssetImportRow:
        data = row.model_dump()
        if data.get("product_name") and not data.get("name"):
            data["name"] = data["product_name"]
        if data.get("owner") and not data.get("owner_user_id"):
            data["owner_user_id"] = data["owner"]
        if data.get("dept") and not data.get("dept_id"):
            data["dept_id"] = data["dept"]
        if data.get("price") is not None and not data.get("purchase_price"):
            data["purchase_price"] = data["price"]

        config = data.get("config") or {}
        if data.get("spec"):
            config["spec"] = data["spec"]
        if data.get("warehouse"):
            config["warehouse"] = data["warehouse"]
        data["config"] = config
        return AssetImportRow(**data)

    @staticmethod
    def list_assets(db: Session) -> list[dict]:
        users = AssetService.users_by_identity(db)
        assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
        changed = False
        rows = []
        for asset in assets:
            user = users.get(asset.owner_user_id or "")
            if user:
                target_dept = user.dept_id or user.dept_name or asset.dept_id
                if asset.owner_user_id != user.user_id:
                    asset.owner_user_id = user.user_id
                    changed = True
                if target_dept and asset.dept_id != target_dept:
                    asset.dept_id = target_dept
                    changed = True
            rows.append(AssetService.to_out(asset, user))
        if changed:
            db.commit()
        return rows

    @staticmethod
    def update_asset(db: Session, asset_id: str, payload: AssetUpdate, operator: str = "system") -> Asset:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("asset not found")

        data = payload.model_dump(exclude_unset=True)
        old_status = asset.status
        for key, value in data.items():
            setattr(asset, key, value)
        AssetService.sync_owner_department(db, asset)

        LifecycleService.record(db, asset.asset_id, "ASSET_UPDATE", old_status, asset.status, operator)
        db.commit()
        db.refresh(asset)
        return AssetService.to_out(asset)

    @staticmethod
    def change_status(
        db: Session,
        asset_id: str,
        to_status: str,
        operator: str = "system",
        owner_user_id: str | None = None,
        dept_id: str | None = None,
        location: str | None = None,
    ) -> Asset:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("asset not found")

        from_status = asset.status
        asset.status = to_status
        if owner_user_id is not None:
            asset.owner_user_id = owner_user_id
        user = AssetService.sync_owner_department(db, asset)
        if dept_id is not None and not user:
            asset.dept_id = dept_id
        if location is not None:
            asset.location = location
        LifecycleService.record(db, asset.asset_id, "STATUS_CHANGE", from_status, to_status, operator)
        db.commit()
        db.refresh(asset)
        return AssetService.to_out(asset, user)

    @staticmethod
    def find_user(db: Session, value: str | None) -> UserDirectory | None:
        if not value:
            return None
        candidates = [value]
        if value.startswith("ldap:"):
            candidates.append(value.removeprefix("ldap:"))
        lowered = value.lower()
        if "cn=" in lowered:
            cn_part = lowered.split("cn=", 1)[1].split(",", 1)[0]
            if cn_part:
                candidates.append(cn_part)
        return (
            db.query(UserDirectory)
            .filter(
                or_(
                    UserDirectory.user_id.in_(candidates),
                    UserDirectory.username.in_(candidates),
                    UserDirectory.external_id.in_(candidates),
                    UserDirectory.email.in_(candidates),
                )
            )
            .first()
        )

    @staticmethod
    def sync_owner_department(db: Session, asset: Asset) -> UserDirectory | None:
        user = AssetService.find_user(db, asset.owner_user_id)
        if not user:
            return None
        asset.owner_user_id = user.user_id
        asset.dept_id = user.dept_id or user.dept_name or asset.dept_id
        return user

    @staticmethod
    def users_by_identity(db: Session) -> dict[str, UserDirectory]:
        users = db.query(UserDirectory).all()
        mapping: dict[str, UserDirectory] = {}
        for user in users:
            for value in [user.user_id, user.username, user.external_id, user.email]:
                if value:
                    mapping[value] = user
        return mapping

    @staticmethod
    def to_out(asset: Asset, user: UserDirectory | None = None) -> dict:
        user = user or None
        return {
            "asset_id": asset.asset_id,
            "name": asset.name,
            "category": asset.category,
            "brand": asset.brand,
            "model": asset.model,
            "sn": asset.sn,
            "config": asset.config,
            "purchase_price": asset.purchase_price,
            "purchase_date": asset.purchase_date,
            "purchase_approval_no": asset.purchase_approval_no,
            "purchase_supplier_name": asset.purchase_supplier_name,
            "warranty_expire_date": asset.warranty_expire_date,
            "warranty_months": asset.warranty_months,
            "status": asset.status,
            "owner_user_id": asset.owner_user_id,
            "owner_display_name": user.display_name if user else None,
            "owner_username": user.username if user else None,
            "dept_id": asset.dept_id,
            "dept_name": user.dept_name if user else None,
            "location": asset.location,
            "created_at": asset.created_at,
        }

    @staticmethod
    def parse_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def parse_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
