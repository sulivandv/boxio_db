from __future__ import annotations

import os
import re
from functools import lru_cache
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "sim", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "")
    db_schema: str = os.getenv("LICENSE_DB_SCHEMA", "licensing")
    token_secret: str = os.getenv("LICENSE_TOKEN_SECRET", "")
    app_env: str = os.getenv("APP_ENV", "local")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    github_owner: str = os.getenv("GITHUB_OWNER", "sua-conta-ou-empresa")
    github_repo: str = os.getenv("GITHUB_REPO", "boxio-releases")
    update_channel: str = os.getenv("UPDATE_CHANNEL", "stable")

    # Render injeta PORT automaticamente. Localmente usamos 8000.
    port: int = _env_int("PORT", 8000)
    render_external_url: str = os.getenv("RENDER_EXTERNAL_URL", "")

    # Segurança da API administrativa pública.
    # Se vazio, rotas /admin ficam desativadas por segurança.
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")

    # Rate limit simples em memória para fase inicial em Render.
    rate_limit_enabled: bool = _env_bool("RATE_LIMIT_ENABLED", True)
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 60)

    # Pool SQL ajustável para Neon/Render.
    db_pool_size: int = _env_int("DB_POOL_SIZE", 5)
    db_max_overflow: int = _env_int("DB_MAX_OVERFLOW", 10)
    db_pool_recycle_seconds: int = _env_int("DB_POOL_RECYCLE_SECONDS", 1800)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurada.")

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", settings.db_schema or ""):
        raise RuntimeError("LICENSE_DB_SCHEMA inválido. Use apenas letras, números e underscore, iniciando com letra ou underscore.")

    weak_secret = (
        not settings.token_secret
        or settings.token_secret.startswith("troque-por")
        or len(settings.token_secret.strip()) < 32
    )
    if weak_secret and settings.app_env == "production":
        raise RuntimeError("LICENSE_TOKEN_SECRET precisa ter pelo menos 32 caracteres em produção.")

    if settings.rate_limit_per_minute < 1:
        settings.rate_limit_per_minute = 60

    return settings
