"""Verificação online de novas versões disponíveis.

Por padrão, esta versão usa GitHub Releases, uma solução gratuita e simples para
hospedar instaladores, pacotes .zip e o manifesto latest.json. Também mantém
suporte a endpoint JSON direto para cenários futuros.
"""
from __future__ import annotations

import json
import urllib.request
from packaging.version import Version

from src.core.logger import update_logger
from src.core.version import APP_VERSION, PRODUCT_ID, UPDATE_CHANNEL, USE_GITHUB_RELEASES
from src.updater.github_releases import load_manifest_from_latest_release
from src.updater.manifest import UpdateManifest

DEFAULT_UPDATE_ENDPOINT = "https://raw.githubusercontent.com/SEU_USUARIO/boxio-releases/main/latest.json"


def fetch_json(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": f"{PRODUCT_ID}/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_for_update(endpoint: str | None = None) -> UpdateManifest | None:
    """Retorna manifesto quando existe versão superior à instalada."""
    logger = update_logger()
    if USE_GITHUB_RELEASES and endpoint is None:
        logger.info("Verificando atualização via GitHub Releases")
        manifest = load_manifest_from_latest_release()
    else:
        endpoint = endpoint or DEFAULT_UPDATE_ENDPOINT
        logger.info("Verificando atualizações em %s", endpoint)
        manifest = UpdateManifest.from_dict(fetch_json(endpoint))

    if manifest.product != PRODUCT_ID:
        raise ValueError("Manifesto pertence a outro produto.")
    if manifest.channel != UPDATE_CHANNEL:
        logger.info("Canal ignorado: %s", manifest.channel)
        return None
    if Version(manifest.latest_version) > Version(APP_VERSION):
        logger.info("Atualização encontrada: %s", manifest.latest_version)
        return manifest
    logger.info("Nenhuma atualização encontrada.")
    return None
