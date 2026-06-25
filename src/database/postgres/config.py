"""Configuração PostgreSQL/Neon para o Boxio.

Prioridade de configuração:
1. BOXIO_DATABASE_URL: URL completa do PostgreSQL/Neon, recomendada para produção.
2. Variáveis separadas POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.

Nunca coloque credenciais diretamente no código. Use arquivo .env local ou
variáveis de ambiente do Windows. O .env não deve ser enviado ao GitHub.
"""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
    ROOT_DIR = Path(__file__).resolve().parents[3]
    load_dotenv(ROOT_DIR / ".env")
except Exception:
    pass


NEON_DIRECT_HOST_EXAMPLE = "ep-billowing-boat-apx4zro0.c-7.us-east-1.aws.neon.tech"
NEON_POOLER_HOST_EXAMPLE = "ep-billowing-boat-apx4zro0-pooler.c-7.us-east-1.aws.neon.tech"


@dataclass(frozen=True)
class PostgresSettings:
    """Parâmetros de conexão do banco.

    No Neon, use sslmode=require. Para pgAdmin/migração/schema, prefira o host
    principal. Para o aplicativo em vários computadores, você pode trocar para
    o pooler após validar tudo.
    """

    database_url: str | None = os.getenv("BOXIO_DATABASE_URL")
    database_url_pooler: str | None = os.getenv("BOXIO_DATABASE_URL_POOLER")
    use_pooler: bool = os.getenv("BOXIO_DB_USE_POOLER", "false").lower() in {"1", "true", "yes", "sim"}
    schema: str = os.getenv("BOXIO_DB_SCHEMA", "boxio")
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "boxio")
    user: str = os.getenv("POSTGRES_USER", "boxio_app")
    password: str = os.getenv("POSTGRES_PASSWORD", "")
    sslmode: str = os.getenv("POSTGRES_SSLMODE", "require")

    def sqlalchemy_url(self) -> str:
        """Retorna a URL final para SQLAlchemy.

        O projeto usa psycopg v3: postgresql+psycopg://...
        Se você copiar uma URL do Neon começando com postgresql://, ela é
        convertida automaticamente para o formato esperado pelo SQLAlchemy.
        """
        if self.use_pooler and self.database_url_pooler:
            return self._normalize_driver(self.database_url_pooler)
        if self.database_url:
            return self._normalize_driver(self.database_url)
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        return (
            f"postgresql+psycopg://{user}:{password}@{self.host}:{self.port}/"
            f"{self.database}?sslmode={self.sslmode}"
        )

    @staticmethod
    def _normalize_driver(url: str) -> str:
        if url.startswith("postgresql+psycopg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def connect_options(self) -> dict[str, str]:
        # search_path garante que o ORM procure as tabelas dentro do schema boxio.
        return {"options": f"-csearch_path={self.schema},public"}
