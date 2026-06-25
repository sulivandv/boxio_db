"""Migração v18: identidade Inovi e inventário demonstrativo limpo.

Esta migração atualiza metadados do banco JSON local para a empresa Inovi sem
apagar produtos reais que o usuário já tenha cadastrado. O inventário modelo com
10 itens fica no arquivo ``database/inventory_db.json`` distribuído com o app; se
já existir um banco persistente em AppData, ele é preservado por segurança.
"""
from __future__ import annotations

version = 18


def up(db: dict) -> dict:
    settings = db.setdefault("settings", {})
    settings.setdefault("app", {})
    settings["app"].update({
        "app_name": "Boxio",
        "product_id": "boxio",
        "company_name": "Inovi",
        "company_display_name": "Inovi",
    })
    db["schema_version"] = version
    db["version"] = max(int(db.get("version", 0) or 0), version)
    return db
