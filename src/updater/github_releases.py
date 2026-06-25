"""Cliente gratuito para GitHub Releases.

O aplicativo consulta a API pública do GitHub para descobrir a última release.
A release deve conter um asset chamado latest.json com o manifesto oficial e um
asset .zip/.exe com o pacote de atualização. Isso evita hospedar servidor pago.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.core.version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO, PRODUCT_ID
from src.updater.manifest import UpdateManifest

GITHUB_API_BASE = "https://api.github.com"


@dataclass(frozen=True)
class GitHubAsset:
    name: str
    download_url: str
    size: int
    content_type: str


def _fetch_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{PRODUCT_ID}/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str, timeout: int = 15) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": f"{PRODUCT_ID}/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def get_latest_release(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> dict[str, Any]:
    """Consulta a última release publicada no repositório configurado."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"
    return _fetch_json(url)


def list_release_assets(release: dict[str, Any]) -> list[GitHubAsset]:
    assets = []
    for asset in release.get("assets", []):
        assets.append(
            GitHubAsset(
                name=asset.get("name", ""),
                download_url=asset.get("browser_download_url", ""),
                size=int(asset.get("size", 0) or 0),
                content_type=asset.get("content_type", ""),
            )
        )
    return assets


def load_manifest_from_latest_release(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> UpdateManifest:
    """Obtém o latest.json anexado à última release do GitHub."""
    release = get_latest_release(owner, repo)
    assets = list_release_assets(release)
    manifest_asset = next((asset for asset in assets if asset.name == "latest.json"), None)
    if not manifest_asset:
        raise FileNotFoundError("A release mais recente não possui o asset latest.json.")
    data = json.loads(_fetch_text(manifest_asset.download_url))

    # Facilita publicação: se o latest.json não tiver URL explícita, tenta localizar
    # automaticamente o pacote principal pela lista de assets da release.
    if not data.get("download_url"):
        package = next((a for a in assets if a.name.endswith((".zip", ".exe")) and a.name != "latest.json"), None)
        if package:
            data["download_url"] = package.download_url
    return UpdateManifest.from_dict(data)
