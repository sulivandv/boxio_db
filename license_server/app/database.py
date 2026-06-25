from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Garante que todas as conexões PostgreSQL usem o schema de licenciamento.
# Isso é importante no Render, porque Base.metadata.create_all pode abrir uma
# conexão nova, diferente da usada em init_schema().
connect_args = {}
if settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
    connect_args = {"options": f"-csearch_path={settings.db_schema},public"}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        # Garante que queries sem schema explícito encontrem as tabelas.
        db.execute(text(f"SET search_path TO {settings.db_schema}, public"))
        yield db
    finally:
        db.close()


def init_schema() -> None:
    """Cria o schema/tabelas quando o servidor sobe.

    Para produção maior, substitua por Alembic. Para a Fase 1 Render + Neon,
    esta abordagem mantém a implantação simples e reduz dependências.
    """
    from app.models import Base  # noqa

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        conn.execute(text(f"SET search_path TO {settings.db_schema}, public"))

    # Extensão não é obrigatória para o servidor atual, porque UUIDs são gerados
    # pela aplicação. Em usuários Neon com permissão limitada, CREATE EXTENSION
    # pode falhar; por isso não deve impedir o deploy.
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    except Exception:
        pass

    Base.metadata.create_all(bind=engine)


def db_ping() -> bool:
    """Teste leve de conectividade para diagnóstico de produção."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
