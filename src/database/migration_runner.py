"""Executor de migrações do banco JSON local.

Mesmo com a adoção do PostgreSQL/Neon, o JSON local continua existindo como
backup/fallback e como fonte para migração. Este runner aplica pequenas
transformações compatíveis entre versões antigas e novas sem apagar dados.
"""
from __future__ import annotations

from importlib import import_module

MIGRATION_MODULES = [
    "src.database.migrations.migration_014_update_infra",
    "src.database.migrations.migration_016_boxio_identity",
    "src.database.migrations.migration_017_neon_postgres_integration",
    "src.database.migrations.migration_018_inovi_demo_inventory",
]


def run_migrations(db: dict) -> dict:
    current = int(db.get("schema_version", 1) or 1)
    for module_name in MIGRATION_MODULES:
        module = import_module(module_name)
        version = int(getattr(module, "version", None) or getattr(module, "VERSION"))
        if version > current:
            db = module.up(db)
            current = version
    return db
