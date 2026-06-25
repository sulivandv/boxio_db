"""Orquestração do fluxo de atualização do aplicativo via GitHub Releases.

O fluxo seguro é:
1. verificar release no GitHub;
2. baixar pacote;
3. validar SHA-256;
4. criar backup dos dados persistentes;
5. executar atualização manual/externa;
6. registrar logs e permitir rollback do backup em caso de erro.
"""
from __future__ import annotations

import json
import subprocess
import sys
import webbrowser
from pathlib import Path

from src.core.backup import create_data_backup
from src.core.logger import update_logger
from src.core.paths import VERSION_FILE, ensure_app_dirs
from src.core.version import APP_VERSION, DB_SCHEMA_VERSION
from src.updater.downloader import download_update
from src.updater.update_checker import check_for_update
from src.updater.manifest import UpdateManifest


def write_local_version() -> None:
    ensure_app_dirs()
    VERSION_FILE.write_text(
        json.dumps({"app_version": APP_VERSION, "db_schema_version": DB_SCHEMA_VERSION}, indent=2),
        encoding="utf-8",
    )


def prepare_update(manifest: UpdateManifest) -> Path:
    """Cria backup, baixa pacote e valida integridade antes da instalação."""
    logger = update_logger()
    logger.info("Preparando atualização para %s", manifest.latest_version)
    backup = create_data_backup(f"pre_update_{manifest.latest_version}")
    logger.info("Backup criado: %s", backup)
    package = download_update(manifest)
    logger.info("Pacote baixado e validado: %s", package)
    return package


def open_manual_download(manifest: UpdateManifest) -> None:
    """Abre a página/instalador oficial para atualização manual assistida."""
    url = manifest.installer_url or manifest.download_url
    if not url:
        raise ValueError("Não há URL de download no manifesto.")
    webbrowser.open(url)


def launch_external_updater(package_path: Path) -> None:
    """Executa updater externo no Windows.

    O app principal não deve substituir a si mesmo enquanto está aberto. Em
    produção, empacote um updater.exe separado, responsável por aguardar o PID
    do app fechar, trocar os arquivos e reabrir o programa.
    """
    updater = Path(sys.executable).with_name("updater.exe")
    if not updater.exists():
        raise FileNotFoundError(
            "updater.exe não encontrado. Use atualização manual ou inclua o atualizador externo no build."
        )
    subprocess.Popen([str(updater), "--package", str(package_path), "--pid", str(__import__("os").getpid())])


def check_download_and_install(auto_install: bool = False) -> str:
    """Fluxo único para botões de atualização manual/automática.

    Retorna texto amigável para ser exibido na UI.
    """
    logger = update_logger()
    try:
        manifest = check_for_update()
        if not manifest:
            return "O sistema já está atualizado."
        package = prepare_update(manifest)
        if auto_install:
            launch_external_updater(package)
            return "Atualização preparada. O instalador será executado para concluir o processo."
        open_manual_download(manifest)
        return "Atualização disponível. O download oficial foi aberto para instalação manual."
    except Exception as exc:
        logger.exception("Falha no fluxo de atualização")
        return f"Não foi possível concluir a atualização: {exc}"
