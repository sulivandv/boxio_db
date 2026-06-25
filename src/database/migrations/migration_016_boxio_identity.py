"""Migração v16: identidade Boxio e preparação comercial.

Atualiza metadados do banco JSON local para a identidade Boxio sem apagar dados existentes.
"""
from __future__ import annotations

VERSION = 16
version = VERSION


def up(db: dict) -> dict:
    db.setdefault("settings", {})
    db["settings"].setdefault("app", {})
    db["settings"]["app"].update({"product_id": "boxio", "app_name": "Boxio"})
    db["settings"].setdefault("updates", {})
    db["settings"]["updates"].setdefault("provider", "github_releases")
    db["settings"]["updates"].setdefault("repo", "boxio-releases")
    db.setdefault("license", {"status": "trial", "plan": "local", "expires_at": ""})
    db["schema_version"] = VERSION
    db["version"] = max(int(db.get("version", 1) or 1), VERSION)
    return db
