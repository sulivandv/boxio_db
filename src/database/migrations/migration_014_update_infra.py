"""Migração v14: metadados para atualização, licença e compatibilidade."""
from __future__ import annotations

VERSION = 14
version = VERSION


def up(db: dict) -> dict:
    db.setdefault("settings", {})
    db["settings"].setdefault("updates", {"channel": "stable", "auto_check": True, "auto_download": False})
    db.setdefault("license", {"status": "trial", "plan": "local", "expires_at": ""})
    db.setdefault("update_history", [])
    db.setdefault("schema_version", VERSION)
    return db
