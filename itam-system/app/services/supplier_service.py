from datetime import datetime

from sqlalchemy.orm import Session

from app.models.purchase import Purchase
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierSave


class SupplierService:
    @staticmethod
    def list_suppliers(db: Session, keyword: str | None = None) -> list[dict]:
        SupplierService.ensure_from_purchases(db)
        rows = db.query(Supplier).order_by(Supplier.id.desc()).all()
        if keyword:
            lowered = keyword.lower()
            rows = [row for row in rows if lowered in row.name.lower() or lowered in (row.contact or "").lower()]
        return [SupplierService.with_stats(db, row) for row in rows]

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
    def purchase_devices(db: Session, supplier_name: str) -> list[dict]:
        if supplier_name == "未指定供应商":
            purchases = (
                db.query(Purchase)
                .filter((Purchase.supplier_name.is_(None)) | (Purchase.supplier_name == ""))
                .order_by(Purchase.id.desc())
                .all()
            )
        else:
            purchases = db.query(Purchase).filter(Purchase.supplier_name == supplier_name).order_by(Purchase.id.desc()).all()
        status_map = {"created": "审批中", "pending_acceptance": "待验收", "received": "已入库"}
        rows = []
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
        return rows

    @staticmethod
    def ensure_from_purchases(db: Session) -> None:
        purchases = db.query(Purchase).all()
        names = {purchase.supplier_name or "未指定供应商" for purchase in purchases}
        changed = False
        for name in names:
            if not db.query(Supplier).filter(Supplier.name == name).first():
                db.add(
                    Supplier(
                        supplier_no=SupplierService.generate_supplier_no(db),
                        name=name,
                        level="普通",
                        status="启用",
                    )
                )
                changed = True
        if changed:
            db.commit()

    @staticmethod
    def with_stats(db: Session, supplier: Supplier) -> dict:
        if supplier.name == "未指定供应商":
            purchases = db.query(Purchase).filter((Purchase.supplier_name.is_(None)) | (Purchase.supplier_name == "")).all()
        else:
            purchases = db.query(Purchase).filter(Purchase.supplier_name == supplier.name).all()
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
            "device_count": sum(sum(item.quantity or 0 for item in purchase.items) for purchase in purchases),
            "total_amount": sum(purchase.total_amount or 0 for purchase in purchases),
            "last_purchase_no": purchases[-1].purchase_no if purchases else "",
        }

    @staticmethod
    def generate_supplier_no(db: Session) -> str:
        count = db.query(Supplier).count() + 1
        return f"SUP-{count:04d}"
