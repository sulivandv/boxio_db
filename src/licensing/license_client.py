"""Cliente HTTP para servidor de licenças do Boxio.

Endpoints esperados no servidor:

POST /licenses/activate
POST /licenses/validate
POST /licenses/deactivate

Esta camada usa apenas biblioteca padrão para facilitar empacotamento com
PyInstaller. Em produção, publique um serviço simples em FastAPI/Flask,
Supabase Edge Function, Cloudflare Worker ou outro backend HTTPS.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.core.version import APP_VERSION, PRODUCT_ID

def get_license_server_url() -> str:
    """Lê a URL do servidor de licenças no momento de uso.

    Isso evita que BOXIO_LICENSE_SERVER_URL fique vazia quando o módulo é
    importado antes do carregamento do .env.
    """
    return os.getenv("BOXIO_LICENSE_SERVER_URL", "").strip().rstrip("/")


def get_license_timeout() -> int:
    try:
        return int(os.getenv("BOXIO_LICENSE_TIMEOUT", "12"))
    except Exception:
        return 12


@dataclass
class LicenseResponse:
    ok: bool
    status: str = ""
    message: str = ""
    payload: dict[str, Any] | None = None


class LicenseServerClient:
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        # Lê o .env no momento em que o cliente é criado, não no import do módulo.
        self.base_url = (base_url or get_license_server_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else get_license_timeout()

    def configured(self) -> bool:
        return bool(self.base_url)

    def _post(self, path: str, data: dict[str, Any]) -> LicenseResponse:
        if not self.base_url:
            return LicenseResponse(False, "server_not_configured", "Servidor de licenças não configurado.")

        url = f"{self.base_url}{path}"
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"{PRODUCT_ID}/{APP_VERSION}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
                return LicenseResponse(
                    ok=bool(parsed.get("ok", True)),
                    status=str(parsed.get("status", "")),
                    message=str(parsed.get("message", "")),
                    payload=parsed,
                )
        except urllib.error.HTTPError as exc:
            try:
                parsed = json.loads(exc.read().decode("utf-8"))
            except Exception:
                parsed = {}
            return LicenseResponse(
                ok=False,
                status=str(parsed.get("status", f"http_{exc.code}")),
                message=str(parsed.get("message", f"Erro HTTP {exc.code} ao validar licença.")),
                payload=parsed or None,
            )
        except Exception as exc:
            return LicenseResponse(False, "network_error", f"Não foi possível comunicar com o servidor de licenças: {exc}")

    def activate(self, payload: dict[str, Any]) -> LicenseResponse:
        return self._post("/licenses/activate", payload)

    def validate(self, payload: dict[str, Any]) -> LicenseResponse:
        return self._post("/licenses/validate", payload)

    def deactivate(self, payload: dict[str, Any]) -> LicenseResponse:
        return self._post("/licenses/deactivate", payload)
