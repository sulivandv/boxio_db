"""Migração conceitual v17: integração Neon/PostgreSQL.

No armazenamento JSON local, esta migração apenas registra metadados indicando
que o projeto está preparado para PostgreSQL/Neon. A criação das tabelas reais
ocorre pelo arquivo src/database/sql/schema_neon_boxio.sql.
"""

version = 17

def up(db: dict) -> dict:
    db.setdefault("metadata", {})["postgres_neon_ready"] = True
    db.setdefault("metadata", {})["recommended_sql_schema_version"] = 18
    db["schema_version"] = max(int(db.get("schema_version", 1)), version)
    return db
