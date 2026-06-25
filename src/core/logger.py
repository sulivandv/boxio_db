"""Configuração simples de logs para produção desktop."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from src.core.paths import APP_LOG_FILE, UPDATE_LOG_FILE, ensure_app_dirs


def setup_logging() -> None:
    ensure_app_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[RotatingFileHandler(APP_LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")],
    )


def update_logger() -> logging.Logger:
    ensure_app_dirs()
    logger = logging.getLogger("updater")
    if not logger.handlers:
        handler = RotatingFileHandler(UPDATE_LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def app_logger() -> logging.Logger:
    """Logger geral da aplicação.

    Mantém compatibilidade com módulos que precisam registrar eventos
    operacionais, licenciamento, validações e falhas internas.
    """
    ensure_app_dirs()
    logger = logging.getLogger("boxio")
    if not logger.handlers:
        handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
