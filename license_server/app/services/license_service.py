from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, License, DeviceActivation, LicenseEvent
from app.schemas import ActivateRequest, ValidateRequest, DeactivateRequest, LicenseResponse
from app.security import create_activation_token, hash_token, verify_activation_token


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def event(
    db: Session,
    event_type: str,
    event_status: str,
    message: str = "",
    license: License | None = None,
    activation: DeviceActivation | None = None,
    device_fingerprint: str = "",
    device_name: str = "",
    app_version: str = "",
    ip_address: str = "",
) -> None:
    db.add(LicenseEvent(
        license_id=license.id if license else None,
        activation_id=activation.id if activation else None,
        event_type=event_type,
        event_status=event_status,
        message=message,
        device_fingerprint=device_fingerprint,
        device_name=device_name,
        app_version=app_version,
        ip_address=ip_address,
    ))


def license_to_response(license: License, activation: DeviceActivation | None, token: str | None, ok: bool = True, status: str = "active", message: str = "Licença válida.") -> LicenseResponse:
    return LicenseResponse(
        ok=ok,
        status=status,
        message=message,
        license_key=license.license_key,
        activation_id=str(activation.id) if activation else None,
        token=token,
        customer_id=str(license.customer_id),
        company_id=str(license.customer_id),
        company_name=license.customer.company_name if license.customer else "",
        plan=license.plan,
        expires_at=license.expires_at.isoformat(),
        max_users=license.max_users,
        max_devices=license.max_devices,
        allowed_modules=list(license.allowed_modules or []),
    )


def blocked(message: str, status: str = "blocked") -> LicenseResponse:
    return LicenseResponse(ok=False, status=status, message=message)


def find_license(db: Session, license_key: str) -> License | None:
    return db.scalar(select(License).where(License.license_key == license_key.strip()))


def check_license_rules(license: License) -> LicenseResponse | None:
    if not license:
        return blocked("Licença não encontrada.", "not_found")

    status = str(license.status or "").strip().lower()
    license.status = status or "active"

    if not license.customer or not license.customer.active:
        return blocked("Cliente bloqueado ou inativo.", "customer_inactive")

    if license.revoked_at or status in {"revoked", "blocked", "cancelled", "inactive", "suspended"}:
        return blocked("Licença bloqueada ou revogada.", status or "blocked")

    if license.expires_at < date.today():
        if license.status != "expired":
            license.status = "expired"
        return blocked("Licença anual expirada. Renove para continuar usando o Boxio.", "expired")

    if license.status != "active":
        return blocked(f"Licença com status inválido: {license.status}", license.status)

    return None


def enforce_device_limit_on_validation(db: Session, license: License, activation: DeviceActivation) -> LicenseResponse | None:
    """Valida se o dispositivo atual ainda está dentro do limite permitido.

    A ativação já bloqueia novos dispositivos quando o limite é atingido.
    Esta validação adicional protege cenários em que `max_devices` foi reduzido
    depois de várias ativações já existirem.
    """
    if license.max_devices <= 0:
        return blocked("Nenhum dispositivo está autorizado para esta licença.", "device_limit")

    active_activations = list(db.scalars(
        select(DeviceActivation)
        .where(
            DeviceActivation.license_id == license.id,
            DeviceActivation.status == "active",
            DeviceActivation.revoked_at.is_(None),
        )
        .order_by(DeviceActivation.activated_at.asc(), DeviceActivation.id.asc())
    ))

    allowed_ids = {a.id for a in active_activations[:license.max_devices]}
    if activation.id not in allowed_ids:
        return blocked("Este dispositivo excede o limite permitido para a licença.", "device_limit")

    return None


def activate_license(db: Session, payload: ActivateRequest, ip_address: str = "") -> LicenseResponse:
    license = find_license(db, payload.license_key)
    if not license:
        event(db, "activate", "not_found", "Chave de licença não encontrada.", device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Licença não encontrada.", "not_found")

    rule = check_license_rules(license)
    if rule:
        event(db, "activate", rule.status, rule.message, license=license, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return rule

    activation = db.scalar(
        select(DeviceActivation).where(
            DeviceActivation.license_id == license.id,
            DeviceActivation.device_fingerprint == payload.device_fingerprint,
        )
    )

    active_count = db.scalar(
        select(func.count(DeviceActivation.id)).where(
            DeviceActivation.license_id == license.id,
            DeviceActivation.status == "active",
            DeviceActivation.revoked_at.is_(None),
        )
    ) or 0

    if activation and activation.status in {"revoked", "blocked"}:
        event(db, "activate", activation.status, "Dispositivo revogado ou bloqueado.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Este dispositivo está revogado ou bloqueado.", "device_revoked")

    if not activation and active_count >= license.max_devices:
        event(db, "activate", "device_limit", "Limite de dispositivos atingido.", license=license, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Limite de dispositivos atingido para esta licença.", "device_limit")

    if not activation:
        activation = DeviceActivation(
            license_id=license.id,
            customer_id=license.customer_id,
            device_fingerprint=payload.device_fingerprint,
            device_name=payload.device_name,
            app_version=payload.app_version,
            status="active",
            last_seen_at=now_utc(),
        )
        db.add(activation)
        db.flush()
    else:
        activation.device_name = payload.device_name or activation.device_name
        activation.app_version = payload.app_version or activation.app_version
        activation.status = "active"
        activation.last_seen_at = now_utc()

    token = create_activation_token(license.license_key, str(activation.id), payload.device_fingerprint)
    activation.token_hash = hash_token(token)
    activation.last_validation_at = now_utc()
    activation.validation_count = (activation.validation_count or 0) + 1
    license.updated_at = now_utc()

    event(db, "activate", "active", "Licença ativada com sucesso.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
    db.commit()
    db.refresh(license)
    db.refresh(activation)
    return license_to_response(license, activation, token, True, "active", "Licença ativada com sucesso.")


def validate_license(db: Session, payload: ValidateRequest, ip_address: str = "") -> LicenseResponse:
    license = find_license(db, payload.license_key)
    if not license:
        event(db, "validate", "not_found", "Chave de licença não encontrada.", device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Licença não encontrada.", "not_found")

    rule = check_license_rules(license)
    if rule:
        event(db, "validate", rule.status, rule.message, license=license, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return rule

    activation = db.get(DeviceActivation, payload.activation_id)
    if not activation or activation.license_id != license.id:
        event(db, "validate", "activation_not_found", "Ativação não encontrada.", license=license, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Ativação não encontrada para esta licença.", "activation_not_found")

    if activation.device_fingerprint != payload.device_fingerprint:
        event(db, "validate", "device_mismatch", "Fingerprint divergente.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Esta licença foi ativada em outro dispositivo.", "device_mismatch")

    if activation.status in {"revoked", "blocked"} or activation.revoked_at:
        event(db, "validate", "device_revoked", "Dispositivo revogado.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Este dispositivo foi revogado.", "device_revoked")

    device_limit_rule = enforce_device_limit_on_validation(db, license, activation)
    if device_limit_rule:
        event(db, "validate", device_limit_rule.status, device_limit_rule.message, license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return device_limit_rule

    if not verify_activation_token(payload.token, license.license_key, str(activation.id), payload.device_fingerprint):
        event(db, "validate", "invalid_token", "Token inválido.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Token de ativação inválido.", "invalid_token")

    # Também confere hash salvo para permitir revogação indireta por troca de token.
    if activation.token_hash and activation.token_hash != hash_token(payload.token):
        event(db, "validate", "token_hash_mismatch", "Token não corresponde ao hash salvo.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
        db.commit()
        return blocked("Token de ativação inválido.", "invalid_token")

    activation.device_name = payload.device_name or activation.device_name
    activation.app_version = payload.app_version or activation.app_version
    activation.last_seen_at = now_utc()
    activation.last_validation_at = now_utc()
    activation.validation_count = (activation.validation_count or 0) + 1

    event(db, "validate", "active", "Licença validada.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, device_name=payload.device_name, app_version=payload.app_version, ip_address=ip_address)
    db.commit()
    db.refresh(license)
    db.refresh(activation)
    return license_to_response(license, activation, None, True, "active", "Licença válida.")


def deactivate_license(db: Session, payload: DeactivateRequest, ip_address: str = "") -> LicenseResponse:
    validation = ValidateRequest(
        license_key=payload.license_key,
        activation_id=payload.activation_id,
        token=payload.token,
        device_fingerprint=payload.device_fingerprint,
    )
    checked = validate_license(db, validation, ip_address)
    if not checked.ok:
        return checked

    activation = db.get(DeviceActivation, payload.activation_id)
    license = find_license(db, payload.license_key)
    if activation:
        activation.status = "revoked"
        activation.revoked_at = now_utc()
    event(db, "deactivate", "revoked", payload.reason or "Desativação solicitada.", license=license, activation=activation, device_fingerprint=payload.device_fingerprint, ip_address=ip_address)
    db.commit()
    return LicenseResponse(ok=True, status="revoked", message="Dispositivo desativado com sucesso.")
