from datetime import datetime

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.purchase import Purchase
from app.models.scrap import ScrapRequest
from app.models.supplier import Supplier
from app.services.number_service import NumberService
from app.schemas.supplier import SupplierSave


class SupplierService:
    @staticmethod
    def list_suppliers(db: Session, keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        SupplierService.ensure_from_business_data(db)
        query = db.query(Supplier)
        clean_keyword = (keyword or "").strip()
        if clean_keyword:
            pattern = f"%{clean_keyword}%"
            query = query.filter((Supplier.name.like(pattern)) | (Supplier.contact.like(pattern)))
        total = query.count()
        query = query.order_by(Supplier.id.desc())
        if page_size and page_size > 0:
            query = query.offset((max(page, 1) - 1) * page_size).limit(page_size)
        rows = query.all()
        return {"list": [SupplierService.with_stats(db, row) for row in rows], "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def save_supplier(db: Session, payload: SupplierSave, supplier_id: int | None = None) -> dict:
        row = db.get(Supplier, supplier_id) if supplier_id else None
        if not row:
            row = db.query(Supplier).filter(Supplier.name == payload.name).first()
        if not row:
            row = Supplier(supplier_no=SupplierService.generate_supplier_no(db), created_at=datetime.utcnow())
            db.add(row)
        row.name = payload.name
        row.contact = payload.contact
        row.phone = payload.phone
        row.level = payload.level
        row.status = payload.status
        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
        return SupplierService.with_stats(db, row)

    @staticmethod
    def ensure_supplier(db: Session, name: str | None) -> Supplier | None:
        clean_name = (name or "").strip()
        if not clean_name:
            return None
        row = db.query(Supplier).filter(Supplier.name == clean_name).first()
        if row:
            return row
        row = Supplier(
            supplier_no=SupplierService.generate_supplier_no(db),
            name=clean_name,
            level="普通",
            status="启用",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def purchase_devices(db: Session, supplier_name: str, page: int = 1, page_size: int = 20) -> dict:
        purchases = SupplierService.purchase_query(db, supplier_name).order_by(Purchase.id.desc()).all()
        rows = []
        status_map = {"created": "待验收", "pending_acceptance": "待验收", "received": "已入库"}
        for purchase in purchases:
            for item in purchase.items:
                rows.append(
                    {
                        "supplier_name": supplier_name,
                        "purchase_no": purchase.purchase_no,
                        "status": status_map.get(purchase.status, purchase.status),
                        "product_name": item.name,
                        "category": item.category,
                        "brand": item.brand,
                        "model": item.model,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_amount": (item.quantity or 0) * (item.unit_price or 0),
                        "warehouse": item.location,
                        "dept": item.dept_id,
                    }
                )

        for asset in SupplierService.asset_query(db, supplier_name).order_by(Asset.created_at.desc()).all():
            rows.append(
                {
                    "supplier_name": supplier_name,
                    "purchase_no": asset.purchase_approval_no or "-",
                    "status": asset.status,
                    "product_name": asset.name,
                    "category": asset.category,
                    "brand": asset.brand,
                    "model": asset.model,
                    "quantity": 1,
                    "unit_price": asset.purchase_price or 0,
                    "total_amount": asset.purchase_price or 0,
                    "warehouse": (asset.config or {}).get("warehouse") or asset.location,
                    "dept": asset.dept_id,
                }
            )
        total = len(rows)
        if page_size and page_size > 0:
            start = (max(page, 1) - 1) * page_size
            rows = rows[start : start + page_size]
        return {"list": rows, "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def ensure_from_business_data(db: Session) -> None:
        purchases = db.query(Purchase).all()
        assets = db.query(Asset).all()
        scraps = db.query(ScrapRequest).filter(ScrapRequest.disposal_method == "变卖").all()
        names = {purchase.supplier_name for purchase in purchases if purchase.supplier_name}
        names.update(asset.purchase_supplier_name for asset in assets if asset.purchase_supplier_name)
        names.update(scrap.dispose_recipient_name for scrap in scraps if scrap.dispose_recipient_name)
        changed = False
        for name in names:
            if not db.query(Supplier).filter(Supplier.name == name).first():
                SupplierService.ensure_supplier(db, name)
                changed = True
        if changed:
            db.commit()

    @staticmethod
    def with_stats(db: Session, supplier: Supplier) -> dict:
        purchases = SupplierService.purchase_query(db, supplier.name).all()
        assets = SupplierService.asset_query(db, supplier.name).all()
        recycled_assets = SupplierService.recycled_assets_query(db, supplier.name).all()
        purchase_amount = sum(purchase.total_amount or 0 for purchase in purchases)
        asset_amount = sum(asset.purchase_price or 0 for asset in assets)
        recycled_amount = sum(scrap.final_residual_value or 0 for scrap in recycled_assets)
        return {
            "id": supplier.id,
            "supplier_no": supplier.supplier_no,
            "name": supplier.name,
            "contact": supplier.contact,
            "phone": supplier.phone,
            "level": supplier.level,
            "status": supplier.status,
            "created_at": supplier.created_at,
            "updated_at": supplier.updated_at,
            "purchase_count": len(purchases),
            "device_count": sum(sum(item.quantity or 0 for item in purchase.items) for purchase in purchases) + len(assets),
            "total_amount": purchase_amount + asset_amount,
            "recycle_count": len(recycled_assets),
            "recycle_amount": recycled_amount,
            "last_purchase_no": purchases[-1].purchase_no if purchases else "",
        }

    @staticmethod
    def recycled_assets(db: Session, supplier_name: str, page: int = 1, page_size: int = 20) -> dict:
        rows = []
        requests = SupplierService.recycled_assets_query(db, supplier_name).order_by(ScrapRequest.disposed_at.desc(), ScrapRequest.id.desc()).all()
        asset_ids = [item.asset_id for item in requests if item.asset_id]
        asset_map = {asset.asset_id: asset for asset in db.query(Asset).filter(Asset.asset_id.in_(asset_ids)).all()} if asset_ids else {}
        for item in requests:
            asset = asset_map.get(item.asset_id)
            rows.append(
                {
                    "request_no": item.request_no,
                    "asset_id": item.asset_id,
                    "asset_no": asset.asset_no if asset else item.asset_id,
                    "asset_name": item.asset_name or (asset.name if asset else ""),
                    "category": item.category or (asset.category if asset else ""),
                    "brand": item.brand or (asset.brand if asset else ""),
                    "model": item.model or (asset.model if asset else ""),
                    "sn": item.asset_sn or (asset.sn if asset else ""),
                    "purchase_price": item.purchase_price or (asset.purchase_price if asset else 0),
                    "estimated_residual_value": item.estimated_residual_value or 0,
                    "final_residual_value": item.final_residual_value or 0,
                    "retirement_date": item.retirement_date,
                    "retirement_approval_no": item.retirement_approval_no or "",
                    "disposed_at": item.disposed_at,
                    "disposal_remark": item.disposal_remark or "",
                    "status": item.status,
                }
            )
        total = len(rows)
        if page_size and page_size > 0:
            start = (max(page, 1) - 1) * page_size
            rows = rows[start : start + page_size]
        return {"list": rows, "total": total, "page": max(page, 1), "page_size": page_size or total}

    @staticmethod
    def purchase_query(db: Session, supplier_name: str):
        if supplier_name == "未指定供应商":
            return db.query(Purchase).filter((Purchase.supplier_name.is_(None)) | (Purchase.supplier_name == ""))
        return db.query(Purchase).filter(Purchase.supplier_name == supplier_name)

    @staticmethod
    def asset_query(db: Session, supplier_name: str):
        if supplier_name == "未指定供应商":
            return db.query(Asset).filter((Asset.purchase_supplier_name.is_(None)) | (Asset.purchase_supplier_name == ""))
        return db.query(Asset).filter(Asset.purchase_supplier_name == supplier_name)

    @staticmethod
    def recycled_assets_query(db: Session, supplier_name: str):
        query = db.query(ScrapRequest).filter(ScrapRequest.disposal_method == "变卖", ScrapRequest.status == "已处置")
        if supplier_name == "未指定供应商":
            return query.filter((ScrapRequest.dispose_recipient_name.is_(None)) | (ScrapRequest.dispose_recipient_name == ""))
        return query.filter(ScrapRequest.dispose_recipient_name == supplier_name)

    @staticmethod
    def generate_supplier_no(db: Session) -> str:
        return NumberService.next(db, "supplier", "SUP-", 4)
