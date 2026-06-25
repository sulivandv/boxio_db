"""Licenciamento anual empresarial do Boxio.

Objetivos:
- ativação online por chave;
- vínculo por dispositivo;
- expiração automática;
- validação periódica;
- tolerância offline controlada;
- suporte a revogação/renovação pelo servidor;
- preparação para planos mensais, filiais, usuários e módulos.

Importante: esta camada protege o uso comercial do executável, mas nenhum
licenciamento client-side impede engenharia reversa por completo. Para produção,
combine com assinatura de instalador, HTTPS, logs no servidor, ofuscação básica
e validação periódica online.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.core.logger import app_logger
from src.core.paths import LICENSE_FILE, ensure_app_dirs
from src.core.version import APP_VERSION
from src.licensing.device import get_device_fingerprint, get_device_name
from src.licensing.license_client import LicenseServerClient

def get_offline_grace_days() -> int:
    try:
        return int(os.getenv("BOXIO_LICENSE_OFFLINE_GRACE_DAYS", "7"))
    except Exception:
        return 7

DEFAULT_LICENSE = {
    "license_key": "",
    "activation_id": "",
    "token": "",
    "customer_id": "",
    "company_name": "",
    "plan": "",
    "status": "not_activated",
    "expires_at": "",
    "max_users": 0,
    "max_devices": 0,
    "allowed_modules": [],
    "device_fingerprint": "",
    "device_name": "",
    "activated_at": "",
    "last_online_check": "",
    "next_online_check": "",
    "server_url": "",
    "app_version_at_activation": "",
}


@dataclass
class LicenseStatus:
    allowed: bool
    status: str
    message: str
    expires_at: str = ""
    offline_mode: bool = False
    days_remaining: int | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat(timespec="seconds")


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


class LicenseManager:
    def __init__(self, path: Path = LICENSE_FILE, client: LicenseServerClient | None = None):
        ensure_app_dirs()
        self.path = Path(path)
        self.client = client or LicenseServerClient()
        if not self.path.exists():
            self.save(DEFAULT_LICENSE.copy())

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            merged = DEFAULT_LICENSE.copy()
            merged.update(data)
            return merged
        except Exception:
            return DEFAULT_LICENSE.copy()

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_activated(self) -> bool:
        data = self.load()
        return bool(data.get("license_key") and data.get("token") and data.get("activation_id"))

    def device_matches(self, data: dict[str, Any]) -> bool:
        local_fp = get_device_fingerprint()
        saved = data.get("device_fingerprint")
        return not saved or saved == local_fp

    def days_remaining(self, expires_at: str | None) -> int | None:
        exp = parse_date(expires_at)
        if not exp:
            return None
        return (exp - date.today()).days

    def local_status(self) -> LicenseStatus:
        data = self.load()
        if not self.is_activated():
            return LicenseStatus(False, "not_activated", "O Boxio ainda não foi ativado neste dispositivo.")

        if not self.device_matches(data):
            return LicenseStatus(False, "device_mismatch", "A licença local pertence a outro dispositivo.")

        if data.get("status") in {"revoked", "blocked", "expired", "cancelled"}:
            return LicenseStatus(False, str(data.get("status")), "A licença está bloqueada, expirada ou revogada.")

        remaining = self.days_remaining(data.get("expires_at"))
        if remaining is not None and remaining < 0:
            return LicenseStatus(False, "expired", "A licença anual venceu. Renove para continuar usando o sistema.", data.get("expires_at", ""), False, remaining)

        return LicenseStatus(True, str(data.get("status") or "active"), "Licença local válida.", data.get("expires_at", ""), False, remaining)

    def online_check_due(self) -> bool:
        data = self.load()
        next_check = parse_datetime(data.get("next_online_check"))
        if not next_check:
            return True
        return now_utc() >= next_check

    def offline_grace_valid(self) -> bool:
        data = self.load()
        last = parse_datetime(data.get("last_online_check"))
        if not last:
            return False
        return now_utc() - last <= timedelta(days=get_offline_grace_days())

    def normalize_server_payload(self, payload: dict[str, Any], original_key: str) -> dict[str, Any]:
        data = self.load()
        data.update({
            "license_key": payload.get("license_key") or original_key,
            "activation_id": payload.get("activation_id") or data.get("activation_id", ""),
            "token": payload.get("token") or data.get("token", ""),
            "customer_id": payload.get("customer_id") or payload.get("company_id") or data.get("customer_id", ""),
            "company_name": payload.get("company_name") or data.get("company_name", ""),
            "plan": payload.get("plan") or data.get("plan", "profissional"),
            "status": payload.get("status") or "active",
            "expires_at": payload.get("expires_at") or data.get("expires_at", ""),
            "max_users": int(payload.get("max_users") or data.get("max_users") or 5),
            "max_devices": int(payload.get("max_devices") or data.get("max_devices") or 1),
            "allowed_modules": payload.get("allowed_modules") or data.get("allowed_modules") or ["inventory", "purchases", "reports"],
            "device_fingerprint": get_device_fingerprint(),
            "device_name": get_device_name(),
            "last_online_check": iso_now(),
            "next_online_check": (now_utc() + timedelta(hours=24)).isoformat(timespec="seconds"),
            "server_url": self.client.base_url,
            "app_version_at_activation": APP_VERSION,
        })
        if not data.get("activated_at"):
            data["activated_at"] = iso_now()
        return data

    def activation_payload(self, license_key: str, company_name: str = "") -> dict[str, Any]:
        return {
            "license_key": license_key.strip(),
            "company_name": company_name.strip(),
            "device_fingerprint": get_device_fingerprint(),
            "device_name": get_device_name(),
            "app_version": APP_VERSION,
            "platform": os.name,
        }

    def activate(self, license_key: str, company_name: str = "") -> LicenseStatus:
        logger = app_logger()
        license_key = (license_key or "").strip()
        if not license_key:
            return LicenseStatus(False, "empty_key", "Informe uma chave de licença.")

        if not self.client.configured():
            return LicenseStatus(False, "server_not_configured", "Servidor de licenças não configurado. Defina BOXIO_LICENSE_SERVER_URL no .env.")

        response = self.client.activate(self.activation_payload(license_key, company_name))
        if not response.ok:
            logger.warning("Falha na ativação: %s", response.message)
            return LicenseStatus(False, response.status or "activation_failed", response.message or "Licença inválida ou não autorizada.")

        data = self.normalize_server_payload(response.payload or {}, license_key)
        self.save(data)
        logger.info("Licença ativada: empresa=%s plano=%s expira=%s", data.get("company_name"), data.get("plan"), data.get("expires_at"))
        return self.local_status()

    def validate_online(self, force: bool = False) -> LicenseStatus:
        """Valida a licença local e, quando necessário, consulta o servidor.

        Correção importante:
        - estados inválidos retornados pelo servidor agora bloqueiam sempre;
        - tolerância offline só é usada para falhas reais de comunicação;
        - validação forçada ignora o cache `next_online_check`.
        """
        logger = app_logger()
        local = self.local_status()
        if not local.allowed:
            return local

        if not self.client.configured():
            if self.offline_grace_valid():
                return LicenseStatus(True, "offline_grace", "Servidor de licenças não configurado. Uso liberado temporariamente pela tolerância offline.", local.expires_at, True, local.days_remaining)
            return LicenseStatus(False, "server_not_configured", "Servidor de licenças não configurado e tolerância offline expirada.", local.expires_at)

        if not force and not self.online_check_due():
            return local

        data = self.load()
        response = self.client.validate({
            "license_key": data.get("license_key"),
            "activation_id": data.get("activation_id"),
            "token": data.get("token"),
            "device_fingerprint": get_device_fingerprint(),
            "device_name": get_device_name(),
            "app_version": APP_VERSION,
        })

        if not response.ok:
            status = response.status or "validation_failed"
            message = response.message or "Licença inválida ou não autorizada."
            logger.warning("Validação online falhou: status=%s mensagem=%s", status, message)

            # Só permite tolerância offline quando a falha parece ser de rede/servidor.
            # Se o servidor respondeu que a licença é inválida, revogada, expirada,
            # dispositivo não autorizado, token inválido etc., o acesso é bloqueado.
            transient_statuses = {"network_error", "timeout", "server_unavailable", "server_not_configured"}
            is_http_5xx = status.startswith("http_5")
            is_http_429 = status == "http_429"

            if status in transient_statuses or is_http_5xx or is_http_429:
                if self.offline_grace_valid():
                    return LicenseStatus(True, "offline_grace", "Não foi possível validar online agora. Uso liberado temporariamente pela tolerância offline.", local.expires_at, True, local.days_remaining)
                return LicenseStatus(False, "offline_grace_expired", "Não foi possível validar a licença online e a tolerância offline expirou.", local.expires_at)

            # Qualquer outro retorno negativo do servidor é considerado bloqueante.
            data["status"] = status
            data["last_online_check"] = iso_now()
            data["next_online_check"] = iso_now()
            self.save(data)
            return LicenseStatus(False, status, message, data.get("expires_at", ""))

        updated = self.normalize_server_payload(response.payload or {}, data.get("license_key", ""))
        self.save(updated)
        return self.local_status()

    def ensure_valid(self, force_online: bool = True) -> LicenseStatus:
        """Validação executada antes de liberar o acesso ao sistema.

        Por padrão força uma consulta online sempre que o servidor estiver
        configurado. Isso evita que cache local ou `next_online_check` permita
        abrir o Boxio depois de uma licença ser revogada/vencida no servidor.
        """
        return self.validate_online(force=force_online)

    def revoke_local(self) -> None:
        data = self.load()
        data["status"] = "revoked"
        self.save(data)

    def clear_local_license(self) -> None:
        self.save(DEFAULT_LICENSE.copy())
