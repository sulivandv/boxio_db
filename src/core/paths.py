"""Caminhos oficiais e persistentes do Boxio.

Em software desktop comercial, arquivos do programa e dados do cliente devem ficar separados.
Atualizações substituem apenas a aplicação instalada; dados, configurações, logs, licença e
banco local permanecem no perfil do usuário.

Este módulo deve ser a única fonte de caminhos do projeto. Evite criar caminhos fixos em telas
ou serviços, pois isso dificulta atualização, backup, migração e suporte técnico.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

try:
    from platformdirs import user_data_dir, user_config_dir, user_cache_dir, user_log_dir
except Exception:  # fallback simples caso a dependência ainda não esteja instalada
    def _base() -> Path:
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    def user_data_dir(appname: str, appauthor: str | None = None): return str(_base() / appname / "Data")
    def user_config_dir(appname: str, appauthor: str | None = None): return str(_base() / appname / "Config")
    def user_cache_dir(appname: str, appauthor: str | None = None): return str(_base() / appname / "Cache")
    def user_log_dir(appname: str, appauthor: str | None = None): return str(_base() / appname / "Logs")

APP_NAME = "Boxio"
APP_AUTHOR = "Inovi"
LEGACY_APP_NAMES = ["ControleDeEstoque", "Controle de estoque", "ControleEstoque"]

# Raiz do projeto/instalação. Em modo empacotado, aponta para a pasta do .exe.
ROOT_DIR = Path(__file__).resolve().parents[2]
BUNDLED_DATABASE_DIR = ROOT_DIR / "database"
BUNDLED_DB_FILE = BUNDLED_DATABASE_DIR / "inventory_db.json"

DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
CONFIG_DIR = Path(user_config_dir(APP_NAME, APP_AUTHOR))
CACHE_DIR = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
LOG_DIR = Path(user_log_dir(APP_NAME, APP_AUTHOR))

DB_DIR = DATA_DIR / "database"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
TEMP_DIR = DATA_DIR / "tmp"
UPDATE_DOWNLOAD_DIR = CACHE_DIR / "updates"

USER_DB_FILE = DB_DIR / "inventory_db.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
LICENSE_FILE = CONFIG_DIR / "license.json"
VERSION_FILE = CONFIG_DIR / "version.json"
UPDATE_LOG_FILE = LOG_DIR / "update.log"
APP_LOG_FILE = LOG_DIR / "app.log"


def ensure_app_dirs() -> None:
    """Cria todos os diretórios persistentes do Boxio.

    A função é segura para chamada repetida e deve ser executada na inicialização.
    """
    for folder in [DATA_DIR, CONFIG_DIR, CACHE_DIR, LOG_DIR, DB_DIR, BACKUP_DIR, EXPORT_DIR, TEMP_DIR, UPDATE_DOWNLOAD_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def _legacy_candidate(filename: str) -> Path | None:
    """Procura arquivos de versões antigas para migração do nome anterior para Boxio.

    Isso evita perda de dados quando o cliente atualiza de versões antigas do sistema para a
    versão renomeada como Boxio.
    """
    for legacy_name in LEGACY_APP_NAMES:
        for resolver in (user_data_dir, user_config_dir):
            try:
                base = Path(resolver(legacy_name, legacy_name))
            except Exception:
                continue
            for candidate in [base / "database" / filename, base / filename, base / "Data" / "database" / filename]:
                if candidate.exists():
                    return candidate
    return None


def copy_legacy_file_if_needed(target: Path, filename: str) -> None:
    """Copia arquivo de instalação anterior somente se o destino atual ainda não existir."""
    if target.exists():
        return
    legacy = _legacy_candidate(filename)
    if legacy and legacy.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)


def ensure_user_database() -> Path:
    """Garante que o banco persistente exista em AppData/Boxio.

    1. Primeiro tenta migrar um banco de versões antigas.
    2. Se não existir, copia o banco modelo que vem com o programa.
    3. Depois disso, nunca sobrescreve o banco existente.
    """
    ensure_app_dirs()
    copy_legacy_file_if_needed(USER_DB_FILE, "inventory_db.json")
    if not USER_DB_FILE.exists() and BUNDLED_DB_FILE.exists():
        shutil.copy2(BUNDLED_DB_FILE, USER_DB_FILE)
    return USER_DB_FILE
