"""Inicialização do banco PostgreSQL/Neon do Boxio.

Executa o arquivo SQL oficial do projeto, criando schema, tabelas, índices e
registros-base. Pode ser usado tanto em desenvolvimento quanto em produção.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from src.database.postgres.connection import engine, check_database_connection

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_FILE = PROJECT_ROOT / "src" / "database" / "sql" / "schema_neon_boxio.sql"


def initialize_database(sql_file: Path = SCHEMA_FILE) -> None:
    """Executa o SQL de criação do schema no banco configurado no .env."""
    if not sql_file.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {sql_file}")
    sql = sql_file.read_text(encoding="utf-8")
    # O driver PostgreSQL aceita múltiplos comandos quando usamos exec_driver_sql.
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)


def main() -> None:
    database, user, schema = check_database_connection()
    print(f"Conexão OK | banco={database} | usuário={user} | schema_atual={schema}")
    initialize_database()
    print("Schema/tabelas do Boxio criados ou atualizados com sucesso.")


if __name__ == "__main__":
    main()
