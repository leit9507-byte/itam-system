import csv
from zipfile import BadZipFile
from datetime import datetime
from io import BytesIO, StringIO
from types import SimpleNamespace
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import UserDirectory
from app.schemas.asset import AssetBatchImport, AssetCreate, AssetImportRow, AssetTextImport, AssetUpdate
from app.services.lifecycle_service import LifecycleService
from app.services.supplier_service import SupplierService


class AssetValidationError(ValueError):
    pass


class AssetService:
    DEFAULT_COMPANY = "未设置公司"
    ASSIGNED_STATUSES = {"in_use", "borrowed"}
    UNASSIGNED_STATUSES = {"pending_purchase", "pending_acceptance", "in_stock", "idle", "ready_scrap"}
    WORKFLOW_STATUSES = {"pending_purchase", "pending_acceptance", "pending_scrap", "scrapped"}
    IMPORT_TEMPLATE_HEADERS = [
        "asset_id",
        "name",
        "category",
        "brand",
        "model",
        "sn",
        "purchase_price",
        "purchase_date",
        "purchase_approval_no",
        "purchase_supplier_name",
        "warranty_years",
        "status",
        "owner_user_id",
        "dept_id",
        "location",
        "company",
        "spec",
        "warehouse",
    ]

    @staticmethod
    def normalize_company(value: str | None) -> str | None:
        clean = (value or "").strip()
        return None if not clean or clean == AssetService.DEFAULT_COMPANY else clean

    @staticmethod
    def normalize_blank(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def validate_status_owner(asset: Asset, *, status_changed: bool = True) -> None:
        status = asset.status
        has_owner = bool(AssetService.normalize_blank(asset.owner_user_id))
        has_location = bool(AssetService.normalize_blank(asset.location))
        if status_changed and status in AssetService.WORKFLOW_STATUSES:
            raise AssetValidationError("待采购、待验收、已提交报废审批、已报废状态由流程控制，不能通过导入或手工状态变更直接设置")
        if status in AssetService.UNASSIGNED_STATUSES and has_owner:
            raise AssetValidationError("待采购、待验收、在库、闲置、待报废状态不能填写使用人/责任人；请清空使用人，或把状态改为 in_use、borrowed、out_stock")
        if status in AssetService.ASSIGNED_STATUSES and not has_owner:
            raise AssetValidationError("在用、借出状态必须填写使用人/责任人")
        if status == "out_stock" and not has_owner and not has_location:
            raise AssetValidationError("已出库状态必须填写使用人/责任人或位置；公用设备请填写位置")

    @staticmethod
    def apply_warranty_expire(asset: Asset) -> None:
        if not asset.purchase_date or not asset.warranty_months:
            return
        asset.warranty_expire_date = AssetService.add_months(asset.purchase_date, asset.warranty_months)

    @staticmethod
    def add_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + int(months)
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, AssetService.days_in_month(year, month))
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def days_in_month(year: int, month: int) -> int:
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - datetime(year, month, 1)).days

    @staticmethod
    def generate_asset_id(db: Session, prefix: str = "ITAM") -> str:
        count = db.query(Asset).count() + 1
        return f"{prefix}-{count:06d}"

    @staticmethod
    def create_asset(db: Session, payload: AssetCreate, operator: str = "system") -> Asset:
        user = AssetService.find_user(db, payload.owner_user_id)
        asset = Asset(
            asset_id=getattr(payload, "asset_id", None) or AssetService.generate_asset_id(db),
            company=AssetService.normalize_company(payload.company),
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
        AssetService.apply_warranty_expire(asset)
        SupplierService.ensure_supplier(db, asset.purchase_supplier_name)
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
                with db.begin_nested():
                    normalized = AssetService.normalize_import_row(row)
                    if normalized.sn and db.query(Asset).filter(Asset.sn == normalized.sn).first():
                        skipped += 1
                        errors.append({"row": index, "message": f"duplicate sn: {normalized.sn}", "data": row.model_dump()})
                        continue
                    if normalized.asset_id and db.get(Asset, normalized.asset_id):
                        skipped += 1
                        errors.append({"row": index, "message": f"duplicate asset_id: {normalized.asset_id}", "data": row.model_dump()})
                        continue
                    AssetService.validate_status_owner(
                        SimpleNamespace(status=normalized.status, owner_user_id=normalized.owner_user_id, location=normalized.location)
                    )

                    asset = Asset(
                        asset_id=normalized.asset_id or AssetService.generate_asset_id(db),
                        company=AssetService.normalize_company(normalized.company),
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
                    AssetService.apply_warranty_expire(asset)
                    AssetService.sync_owner_department(db, asset)
                    SupplierService.ensure_supplier(db, asset.purchase_supplier_name)
                    db.add(asset)
                    db.flush()
                    LifecycleService.record(db, asset.asset_id, "BATCH_IMPORT", None, asset.status, payload.operator)
                    created_assets.append(asset)
            except SQLAlchemyError as exc:
                errors.append({"row": index, "message": f"数据库保存失败：{AssetService.db_error_message(exc)}", "data": row.model_dump()})
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
    def db_error_message(exc: SQLAlchemyError) -> str:
        detail = str(getattr(exc, "orig", exc)).strip()
        if "Duplicate entry" in detail and "assets.sn" in detail:
            return "资产序列号已存在，请检查 SN 是否重复"
        if "Duplicate entry" in detail and "PRIMARY" in detail:
            return "资产编号已存在，请检查 asset_id 是否重复"
        if "Data too long" in detail:
            return "字段内容过长，请检查该行文本长度"
        return detail or "请检查导入数据是否符合要求"

    @staticmethod
    def import_assets_from_text(db: Session, payload: AssetTextImport) -> dict:
        items = AssetService.parse_import_text(payload.content)
        return AssetService.import_assets(db, AssetBatchImport(operator=payload.operator, items=items))

    @staticmethod
    def import_assets_from_excel(db: Session, content: bytes, operator: str = "asset-import") -> dict:
        items = AssetService.parse_import_excel(content)
        return AssetService.import_assets(db, AssetBatchImport(operator=operator, items=items))

    @staticmethod
    def preview_import_assets(db: Session, items: list[AssetImportRow]) -> dict:
        errors: list[dict] = []
        preview_items: list[dict] = []
        seen_sn: set[str] = set()
        seen_asset_id: set[str] = set()

        for index, row in enumerate(items, start=1):
            try:
                normalized = AssetService.normalize_import_row(row)
                if normalized.sn:
                    if normalized.sn in seen_sn or db.query(Asset).filter(Asset.sn == normalized.sn).first():
                        raise AssetValidationError(f"duplicate sn: {normalized.sn}")
                    seen_sn.add(normalized.sn)
                if normalized.asset_id:
                    if normalized.asset_id in seen_asset_id or db.get(Asset, normalized.asset_id):
                        raise AssetValidationError(f"duplicate asset_id: {normalized.asset_id}")
                    seen_asset_id.add(normalized.asset_id)
                AssetService.validate_status_owner(
                    SimpleNamespace(status=normalized.status, owner_user_id=normalized.owner_user_id, location=normalized.location)
                )
                preview_items.append({"row": index, "valid": True, "data": normalized.model_dump(mode="json")})
            except Exception as exc:
                errors.append({"row": index, "message": str(exc), "data": row.model_dump(mode="json")})
                preview_items.append({"row": index, "valid": False, "data": row.model_dump(mode="json")})

        return {
            "total": len(items),
            "valid": len([item for item in preview_items if item["valid"]]),
            "errors": errors,
            "items": preview_items,
        }

    @staticmethod
    def preview_import_text(db: Session, payload: AssetTextImport) -> dict:
        return AssetService.preview_import_assets(db, AssetService.parse_import_text(payload.content))

    @staticmethod
    def preview_import_excel(db: Session, content: bytes) -> dict:
        return AssetService.preview_import_assets(db, AssetService.parse_import_excel(content))

    @staticmethod
    def build_import_template() -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "资产导入"
        sheet.append(AssetService.IMPORT_TEMPLATE_HEADERS)
        sheet.append(
            [
                "",
                "ThinkPad X1 Carbon",
                "笔记本电脑",
                "Lenovo",
                "X1 Carbon Gen 12",
                "SN-IMPORT-001",
                15000,
                "2026-06-24",
                "OA-20260624-001",
                "联想授权供应商",
                3,
                "in_stock",
                "",
                "IT",
                "上海IT仓",
                "总部",
                "32G/1TB",
                "上海IT仓",
            ]
        )
        sheet.append(
            [
                "",
                "Dell U2723QE",
                "显示器",
                "Dell",
                "U2723QE",
                "SN-IMPORT-002",
                3999,
                "2026-06-24",
                "OA-20260624-001",
                "Dell渠道商",
                3,
                "in_use",
                "U-ADMIN",
                "IT",
                "上海办公区",
                "总部",
                "27英寸 4K",
                "上海IT仓",
            ]
        )

        example = workbook.create_sheet("填写示例")
        example.append(AssetService.IMPORT_TEMPLATE_HEADERS)
        for values in sheet.iter_rows(min_row=2, max_row=3, values_only=True):
            example.append(list(values))
        sheet.delete_rows(2, 2)

        header_fill = PatternFill("solid", fgColor="D9EAF7")
        header_font = Font(bold=True)
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
        for cell in example[1]:
            cell.fill = header_fill
            cell.font = header_font

        widths = {
            "A": 18,
            "B": 24,
            "C": 16,
            "D": 16,
            "E": 20,
            "F": 20,
            "G": 16,
            "H": 16,
            "I": 22,
            "J": 22,
            "K": 16,
            "L": 16,
            "M": 18,
            "N": 16,
            "O": 18,
            "P": 18,
            "Q": 20,
            "R": 18,
        }
        for column, width in widths.items():
            sheet.column_dimensions[column].width = width
            example.column_dimensions[column].width = width
        sheet.freeze_panes = "A2"
        example.freeze_panes = "A2"

        status_validation = DataValidation(
            type="list",
            formula1='"in_stock,in_use,idle,borrowed,out_stock,repair,ready_scrap"',
            allow_blank=False,
        )
        sheet.add_data_validation(status_validation)
        status_validation.add("L2:L500")

        instruction = workbook.create_sheet("字段说明")
        instruction.append(["字段", "是否必填", "说明"])
        rows = [
            ("asset_id", "否", "资产编号；留空时系统自动生成"),
            ("name", "是", "资产名称"),
            ("category", "是", "设备类型，如 笔记本电脑、显示器"),
            ("brand", "否", "品牌"),
            ("model", "否", "型号"),
            ("sn", "否", "序列号；重复序列号会跳过导入"),
            ("purchase_price", "否", "采购价格，数字"),
            ("purchase_date", "否", "采购日期，格式 YYYY-MM-DD"),
            ("purchase_approval_no", "否", "采购审批单号或采购单号"),
            ("purchase_supplier_name", "否", "采购供应商"),
            ("warranty_years", "否", "维保年限，系统会换算为月数并计算质保到期"),
            ("status", "是", "可填 in_stock、in_use、idle、borrowed、out_stock、repair、ready_scrap"),
            ("owner_user_id", "按状态", "in_use、borrowed、out_stock 必填；库存/闲置/待报废必须留空"),
            ("dept_id", "否", "部门编号或部门名称"),
            ("location", "否", "当前位置"),
            ("company", "否", "所属公司"),
            ("spec", "否", "规格配置"),
            ("warehouse", "否", "仓库名称"),
        ]
        for row in rows:
            instruction.append(row)
        for cell in instruction[1]:
            cell.fill = header_fill
            cell.font = header_font
        instruction.column_dimensions["A"].width = 24
        instruction.column_dimensions["B"].width = 12
        instruction.column_dimensions["C"].width = 74

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

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
        if not content:
            raise AssetValidationError("Excel 文件为空，请重新选择文件")
        try:
            workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
        except BadZipFile as exc:
            raise AssetValidationError("Excel 文件无法打开，可能不是有效的 .xlsx/.xlsm 文件或文件已损坏") from exc
        except InvalidFileException as exc:
            raise AssetValidationError("Excel 文件格式不支持，请上传 .xlsx 或 .xlsm 文件") from exc
        except Exception as exc:
            raise AssetValidationError(f"Excel 文件解析失败：{exc}") from exc

        sheet = workbook.active
        if not sheet:
            raise AssetValidationError("Excel 文件没有可读取的工作表")
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise AssetValidationError("Excel 工作表为空，请至少保留表头行")

        headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        if not any(headers):
            raise AssetValidationError("Excel 第一行没有表头，请使用导入模板或填写字段名")
        normalized_headers = {header.lower() for header in headers if header}
        name_headers = {"name", "product_name", "资产名称", "产品名称"}
        category_headers = {"category", "device_type", "设备类型", "类别"}
        missing = []
        if not normalized_headers & {value.lower() for value in name_headers}:
            missing.append("资产名称(name)")
        if not normalized_headers & {value.lower() for value in category_headers}:
            missing.append("设备类型(category)")
        if missing:
            raise AssetValidationError(f"Excel 表头缺少必填字段：{', '.join(missing)}")

        items: list[AssetImportRow] = []
        for values in rows[1:]:
            mapping = {
                headers[index]: value
                for index, value in enumerate(values)
                if index < len(headers) and headers[index] and value not in (None, "")
            }
            if mapping:
                items.append(AssetService.row_from_mapping(mapping))
        if not items:
            return []
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
        warranty_years = AssetService.parse_int(pick("warranty_years", "维保年限", "质保年限"))
        warranty_months = warranty_years * 12 if warranty_years is not None else AssetService.parse_int(pick("warranty_months", "质保月数", "维保月数", "质保"))
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
            purchase_price=AssetService.parse_float(price, "采购价格"),
            purchase_date=AssetService.parse_datetime(pick("purchase_date", "采购日期", "采购时间")),
            purchase_approval_no=pick("purchase_approval_no", "采购审批单号", "审批单号", "采购单号"),
            purchase_supplier_name=pick("purchase_supplier_name", "采购供应商", "供应商"),
            warranty_expire_date=AssetService.parse_datetime(pick("warranty_expire_date", "质保到期", "质保到期日")),
            warranty_months=warranty_months,
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
    def list_assets(
        db: Session,
        page: int = 1,
        page_size: int = 0,
        keyword: str | None = None,
        status: str | None = None,
        category: str | None = None,
        company: str | None = None,
        supplier: str | None = None,
    ) -> dict:
        users = AssetService.users_by_identity(db)
        query = db.query(Asset)
        clean_keyword = (keyword or "").strip()
        if clean_keyword:
            pattern = f"%{clean_keyword}%"
            query = query.filter(
                or_(
                    Asset.asset_id.like(pattern),
                    Asset.name.like(pattern),
                    Asset.dept_id.like(pattern),
                    Asset.sn.like(pattern),
                    Asset.brand.like(pattern),
                    Asset.model.like(pattern),
                    Asset.owner_user_id.like(pattern),
                    Asset.purchase_approval_no.like(pattern),
                    Asset.purchase_supplier_name.like(pattern),
                )
            )
        if status:
            query = query.filter(Asset.status == status)
        if category:
            query = query.filter(Asset.category == category)
        if supplier:
            query = query.filter(Asset.purchase_supplier_name == supplier)
        if company:
            stored = AssetService.normalize_company(company)
            query = query.filter(Asset.company.is_(None) if stored is None else Asset.company == stored)

        total = query.count()
        query = query.order_by(Asset.created_at.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        assets = query.all()
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
        return {"list": rows, "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def update_asset(db: Session, asset_id: str, payload: AssetUpdate, operator: str = "system") -> Asset:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("asset not found")

        data = payload.model_dump(exclude_unset=True)
        old_status = asset.status
        should_validate_status_owner = bool({"status", "owner_user_id"} & data.keys())
        for key, value in data.items():
            if key == "company":
                value = AssetService.normalize_company(value)
            if key == "owner_user_id":
                value = AssetService.normalize_blank(value)
            setattr(asset, key, value)
        AssetService.apply_warranty_expire(asset)
        AssetService.sync_owner_department(db, asset)
        if should_validate_status_owner:
            AssetService.validate_status_owner(asset, status_changed=asset.status != old_status)
        SupplierService.ensure_supplier(db, asset.purchase_supplier_name)

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
        remark: str | None = None,
    ) -> Asset:
        asset = db.get(Asset, asset_id)
        if not asset:
            raise ValueError("asset not found")

        from_status = asset.status
        previous_owner_user_id = asset.owner_user_id
        previous_user = AssetService.find_user(db, previous_owner_user_id)
        if owner_user_id is not None:
            asset.owner_user_id = AssetService.normalize_blank(owner_user_id)
        user = AssetService.sync_owner_department(db, asset)
        if dept_id is not None and not user:
            asset.dept_id = dept_id
        if location is not None:
            asset.location = location
        asset.status = to_status
        AssetService.validate_status_owner(asset, status_changed=to_status != from_status)
        lifecycle_remark = AssetService.inventory_lifecycle_remark(
            to_status,
            remark,
            previous_owner_user_id,
            previous_user,
            asset.owner_user_id,
            user,
            asset.location,
        )
        LifecycleService.record(db, asset.asset_id, "STATUS_CHANGE", from_status, to_status, operator, lifecycle_remark)
        db.commit()
        db.refresh(asset)
        return AssetService.to_out(asset, user)

    @staticmethod
    def user_label(user: UserDirectory | None, fallback: str | None) -> str:
        if user:
            return user.display_name or user.username or user.user_id
        return AssetService.normalize_blank(fallback) or "-"

    @staticmethod
    def inventory_lifecycle_remark(
        to_status: str,
        remark: str | None,
        previous_owner_user_id: str | None,
        previous_user: UserDirectory | None,
        owner_user_id: str | None,
        owner_user: UserDirectory | None,
        location: str | None = None,
    ) -> str | None:
        base = AssetService.normalize_blank(remark)
        labels = {
            "in_stock": ("退回人", AssetService.user_label(previous_user, previous_owner_user_id)),
            "in_use": ("领用人", AssetService.user_label(owner_user, owner_user_id)),
            "borrowed": ("借用人", AssetService.user_label(owner_user, owner_user_id)),
            "out_stock": ("出库责任人", AssetService.user_label(owner_user, owner_user_id)),
        }
        if to_status not in labels:
            return base or None
        key, value = labels[to_status]
        if to_status == "in_stock":
            key, value = "入库地址", AssetService.normalize_blank(location) or "-"
        if to_status == "out_stock" and not AssetService.normalize_blank(owner_user_id):
            key, value = "公用设备位置", AssetService.normalize_blank(location) or "-"
        detail = f"{key}: {value}"
        if detail in base:
            return base
        return f"{base}; {detail}" if base else detail

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
            "company": asset.company or AssetService.DEFAULT_COMPANY,
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
    def parse_float(value: Any, field_name: str = "数字") -> float:
        if value in (None, ""):
            return 0
        if isinstance(value, int | float):
            return float(value)
        text = str(value).strip()
        if not text:
            return 0
        normalized = text.replace(",", "").replace("￥", "").replace("¥", "").replace("元", "").replace(" ", "")
        try:
            return float(normalized)
        except ValueError as exc:
            raise AssetValidationError(f"{field_name}格式不正确：{text}，请填写数字，例如 1380.00") from exc

    @staticmethod
    def parse_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(AssetService.parse_float(value))
        except (TypeError, ValueError):
            return None
