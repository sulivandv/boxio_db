from __future__ import annotations

import json
import urllib.request
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["releases"])


def _fetch_json(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "boxio-license-server"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "ok": True,
        "service": "boxio-license-server",
        "environment": settings.app_env,
        "schema": settings.db_schema,
    }


@router.get("/api/releases/latest")
def latest_release():
    """Consulta a última release do GitHub e retorna metadados básicos.

    O desktop pode continuar consultando GitHub Releases diretamente. Este
    endpoint fica preparado para regra futura de versão mínima obrigatória.
    """
    settings = get_settings()
    url = f"https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}/releases/latest"
    release = _fetch_json(url)
    assets = release.get("assets", [])
    manifest_asset = next((a for a in assets if a.get("name") == "latest.json"), None)
    package = next((a for a in assets if str(a.get("name", "")).endswith((".zip", ".exe"))), None)
    return {
        "product": "boxio",
        "channel": settings.update_channel,
        "latest_version": str(release.get("tag_name", "")).lstrip("v"),
        "release_url": release.get("html_url"),
        "manifest_url": manifest_asset.get("browser_download_url") if manifest_asset else None,
        "download_url": package.get("browser_download_url") if package else None,
        "notes": release.get("body", ""),
    }
