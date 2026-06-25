"""Cache local SQLite para acelerar o Boxio desktop.

O PostgreSQL/Neon continua sendo a fonte oficial dos dados, mas a interface
não deve depender da latência da internet para abrir páginas, trocar telas ou
filtrar tabelas. Este módulo grava snapshots e metadados em SQLite local para
que leituras comuns retornem em milissegundos.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.paths import CACHE_DIR, ensure_app_dirs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LocalCache:
    """Pequeno cache persistente local baseado em SQLite.

    O cache armazena coleções completas como JSON. Isso simplifica a integração
    com a UI antiga, que já trabalha com listas de dicionários. Para produção
    futura com muitos registros, este arquivo pode evoluir para tabelas locais
    normalizadas por entidade.
    """

    def __init__(self, path: Path | None = None):
        ensure_app_dirs()
        self.path = Path(path or CACHE_DIR / "boxio_local_cache.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_collections (
                    name TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get_collection(self, name: str) -> list[dict] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM cache_collections WHERE name=?", (name,)).fetchone()
        if not row:
            return None
        try:
            data = json.loads(row[0])
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def set_collection(self, name: str, rows: list[dict]) -> None:
        payload = json.dumps(rows or [], ensure_ascii=False, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cache_collections (name, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
                """,
                (name, payload, utc_now()),
            )

    def invalidate(self, *names: str) -> None:
        if not names:
            return
        with self._connect() as conn:
            conn.executemany("DELETE FROM cache_collections WHERE name=?", [(n,) for n in names])

    def clear_all(self) -> None:
        """Remove snapshots locais sem apagar metadados essenciais do usuário."""
        with self._connect() as conn:
            conn.execute("DELETE FROM cache_collections")

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM cache_meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cache_meta (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, str(value), utc_now()),
            )
