"""Persistência JSON com escrita atômica e migrações automáticas.

O armazenamento local continua simples e legível, mas agora é compatível com
atualizações comerciais: carrega dados de AppData, executa migrações e salva sem
sobrescrever arquivos do cliente durante atualizações do programa.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.database.migration_runner import run_migrations


class JsonStorage:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        # Toda abertura do banco passa pelo runner. Se o app novo espera uma
        # estrutura mais recente, as transformações são aplicadas sem apagar dados.
        return run_migrations(data)

    def save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        tmp.replace(self.path)
