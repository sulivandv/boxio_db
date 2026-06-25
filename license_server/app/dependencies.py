from __future__ import annotations

import hmac
from fastapi import Header, HTTPException, status
from app.config import get_settings


def require_admin_api_key(
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Protege rotas administrativas públicas.

    A Fase 1 publica o servidor no Render. Por isso, endpoints /admin não
    podem ficar abertos na internet. Configure ADMIN_API_KEY no Render e envie
    o mesmo valor no header X-Admin-API-Key ou Authorization: Bearer <chave>.
    """
    settings = get_settings()
    expected = (settings.admin_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API administrativa desativada. Configure ADMIN_API_KEY no ambiente de produção.",
        )

    provided = (x_admin_api_key or "").strip()
    if not provided and authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            provided = value[7:].strip()

    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave administrativa inválida ou ausente.",
        )
