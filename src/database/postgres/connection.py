"""Engine e sessões SQLAlchemy para PostgreSQL/Neon.

Este módulo centraliza a conexão do Boxio com PostgreSQL. Ele foi preparado para:
- Neon com sslmode=require;
- schema dedicado (boxio);
- pool pequeno e seguro para aplicativo desktop;
- transações curtas com commit/rollback;
- teste de conexão e leitura da versão do schema.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from src.database.postgres.config import PostgresSettings


def create_postgres_engine(settings: PostgresSettings | None = None):
    settings = settings or PostgresSettings()
    return create_engine(
        settings.sqlalchemy_url(),
        # Em desktop + Neon, manter pool pequeno evita conexões presas sem necessidade.
        pool_size=3,
        max_overflow=2,
        pool_pre_ping=True,
        pool_recycle=300,
        future=True,
        connect_args=settings.connect_options,
    )


engine = create_postgres_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def db_session() -> Iterator[Session]:
    """Abre uma sessão transacional e garante commit/rollback corretamente."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> tuple[str, str, str]:
    """Valida se o banco está acessível e retorna banco, usuário e schema atual."""
    with engine.connect() as conn:
        row = conn.execute(text("SELECT current_database(), current_user, current_schema()")) .fetchone()
        return row[0], row[1], row[2]


def get_schema_version(default: int = 0) -> int:
    """Lê a versão do schema registrada em boxio.app_metadata."""
    try:
        with engine.connect() as conn:
            value = conn.execute(
                text("SELECT value FROM app_metadata WHERE key = 'schema_version'")
            ).scalar_one_or_none()
            return int(value or default)
    except Exception:
        return default
