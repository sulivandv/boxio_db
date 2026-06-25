"""Gera latest.json para publicação gratuita no GitHub Releases.

Uso:
    python tools/release/build_github_release.py dist/boxio_1.18.0.zip 1.18.0
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Informe: pacote.zip versão")
    package = Path(sys.argv[1])
    version = sys.argv[2]
    if not package.exists():
        raise SystemExit(f"Pacote não encontrado: {package}")

    manifest = {
        "product": "boxio",
        "channel": "stable",
        "latest_version": version,
        "minimum_supported_version": "1.15.0",
        "db_schema_version": 16,
        "mandatory": False,
        "release_date": "PREENCHA_A_DATA",
        "download_url": f"https://github.com/SEU_USUARIO/boxio-releases/releases/download/v{version}/{package.name}",
        "installer_url": "",
        "sha256": sha256_file(package),
        "notes": ["Atualização do Boxio"]
    }
    out = package.parent / "latest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifesto gerado: {out}")
    print(f"SHA-256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
