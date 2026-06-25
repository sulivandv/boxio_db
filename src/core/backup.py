"""Rotinas de backup antes de atualizações e migrações."""
from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from src.core.paths import BACKUP_DIR, DATA_DIR, ensure_app_dirs


def create_data_backup(reason: str = "manual") -> Path:
    """Compacta a pasta de dados do usuário.

    O backup é criado antes de atualizar arquivos ou migrar o banco. Em caso de
    falha, pode ser usado para rollback manual ou automático.
    """
    ensure_app_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}_{reason}.zip"
    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in DATA_DIR.rglob("*"):
            if path.is_file() and path != backup_file:
                zf.write(path, path.relative_to(DATA_DIR))
    return backup_file


def restore_backup(backup_file: Path) -> None:
    """Restaura um backup compactado para a pasta de dados do usuário."""
    backup_file = Path(backup_file)
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup não encontrado: {backup_file}")
    with zipfile.ZipFile(backup_file, "r") as zf:
        zf.extractall(DATA_DIR)
