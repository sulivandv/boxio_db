from __future__ import annotations

from pydantic import BaseModel, Field


class ActivateRequest(BaseModel):
    license_key: str = Field(min_length=5)
    company_name: str = ""
    device_fingerprint: str = Field(min_length=10)
    device_name: str = ""
    app_version: str = ""
    platform: str = ""


class ValidateRequest(BaseModel):
    license_key: str
    activation_id: str
    token: str
    device_fingerprint: str
    device_name: str = ""
    app_version: str = ""


class DeactivateRequest(BaseModel):
    license_key: str
    activation_id: str
    token: str
    device_fingerprint: str
    reason: str = ""


class LicenseResponse(BaseModel):
    ok: bool
    status: str
    message: str = ""
    license_key: str | None = None
    activation_id: str | None = None
    token: str | None = None
    customer_id: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    plan: str | None = None
    expires_at: str | None = None
    max_users: int | None = None
    max_devices: int | None = None
    allowed_modules: list[str] | None = None


class CreateCustomerRequest(BaseModel):
    company_name: str
    document: str | None = None
    email: str | None = None
    phone: str | None = None


class CreateLicenseRequest(BaseModel):
    customer_id: str
    license_key: str
    plan: str = "profissional"
    expires_at: str
    max_devices: int = 5
    max_users: int = 5
    allowed_modules: list[str] = ["inventory", "purchases", "reports"]
