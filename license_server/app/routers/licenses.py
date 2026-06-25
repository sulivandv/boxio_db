from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ActivateRequest, ValidateRequest, DeactivateRequest, LicenseResponse
from app.services.license_service import activate_license, validate_license, deactivate_license

router = APIRouter(tags=["licenses"])


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/licenses/activate", response_model=LicenseResponse)
@router.post("/api/license/activate", response_model=LicenseResponse)
def activate(payload: ActivateRequest, request: Request, db: Session = Depends(get_db)):
    return activate_license(db, payload, client_ip(request))


@router.post("/licenses/validate", response_model=LicenseResponse)
@router.post("/api/license/validate", response_model=LicenseResponse)
@router.post("/api/license/heartbeat", response_model=LicenseResponse)
def validate(payload: ValidateRequest, request: Request, db: Session = Depends(get_db)):
    return validate_license(db, payload, client_ip(request))


@router.post("/licenses/deactivate", response_model=LicenseResponse)
@router.post("/api/license/revoke", response_model=LicenseResponse)
@router.post("/api/license/deactivate", response_model=LicenseResponse)
def deactivate(payload: DeactivateRequest, request: Request, db: Session = Depends(get_db)):
    return deactivate_license(db, payload, client_ip(request))
