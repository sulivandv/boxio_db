from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin_api_key
from app.models import Customer, License
from app.schemas import CreateCustomerRequest, CreateLicenseRequest
from app.services.license_service import now_utc

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])


@router.post("/customers")
def create_customer(payload: CreateCustomerRequest, db: Session = Depends(get_db)):
    customer = Customer(
        company_name=payload.company_name,
        document=payload.document,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"ok": True, "customer_id": str(customer.id), "company_name": customer.company_name}


@router.post("/licenses")
def create_license(payload: CreateLicenseRequest, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    license = License(
        customer_id=customer.id,
        license_key=payload.license_key.strip(),
        plan=payload.plan,
        expires_at=date.fromisoformat(payload.expires_at),
        max_devices=payload.max_devices,
        max_users=payload.max_users,
        allowed_modules=payload.allowed_modules,
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    return {"ok": True, "license_id": str(license.id), "license_key": license.license_key}


@router.post("/licenses/{license_id}/revoke")
def revoke_license(license_id: str, db: Session = Depends(get_db)):
    license = db.get(License, license_id)
    if not license:
        raise HTTPException(status_code=404, detail="Licença não encontrada.")
    license.status = "revoked"
    license.revoked_at = now_utc()
    db.commit()
    return {"ok": True, "status": "revoked"}
