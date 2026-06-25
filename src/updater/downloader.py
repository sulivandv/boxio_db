"""Download seguro de pacotes de atualização."""
from __future__ import annotations

import urllib.request
from pathlib import Path

from src.core.paths import UPDATE_DOWNLOAD_DIR, ensure_app_dirs
from src.updater.manifest import UpdateManifest
from src.updater.verifier import verify_sha256


def download_update(manifest: UpdateManifest) -> Path:
    """Baixa o pacote informado no manifesto e valida SHA-256."""
    ensure_app_dirs()
    if not manifest.download_url:
        raise ValueError("Manifesto sem URL de download.")

    suffix = ".exe" if manifest.download_url.lower().endswith(".exe") else ".zip"
    target = UPDATE_DOWNLOAD_DIR / f"boxio_{manifest.latest_version}{suffix}"
    urllib.request.urlretrieve(manifest.download_url, target)
    verify_sha256(target, manifest.sha256)
    return target
