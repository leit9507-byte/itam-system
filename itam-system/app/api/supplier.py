from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.supplier import SupplierDeviceOut, SupplierOut, SupplierSave
from app.services.supplier_service import SupplierService


router = APIRouter(prefix="/supplier", tags=["Supplier"])


@router.get("/list", response_model=list[SupplierOut])
def list_suppliers(keyword: str | None = None, db: Session = Depends(get_db)):
    return SupplierService.list_suppliers(db, keyword)


@router.post("/save", response_model=SupplierOut)
def save_supplier(payload: SupplierSave, db: Session = Depends(get_db)):
    return SupplierService.save_supplier(db, payload)


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, payload: SupplierSave, db: Session = Depends(get_db)):
    return SupplierService.save_supplier(db, payload, supplier_id)


@router.get("/{supplier_name}/devices", response_model=list[SupplierDeviceOut])
def supplier_devices(supplier_name: str, db: Session = Depends(get_db)):
    return SupplierService.purchase_devices(db, supplier_name)
