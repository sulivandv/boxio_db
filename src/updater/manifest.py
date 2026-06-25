"""Modelo e leitura do manifesto remoto de atualização.

O manifesto é um JSON hospedado online, por exemplo no GitHub Releases, com a
versão mais recente, URL de download, hash SHA-256 e notas da versão.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UpdateManifest:
    product: str
    channel: str
    latest_version: str
    minimum_supported_version: str
    db_schema_version: int
    download_url: str
    sha256: str
    mandatory: bool = False
    release_date: str = ""
    installer_url: str = ""
    signature: str = ""
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateManifest":
        return cls(
            product=data.get("product", "boxio"),
            channel=data.get("channel", "stable"),
            latest_version=data.get("latest_version", "0.0.0"),
            minimum_supported_version=data.get("minimum_supported_version", "0.0.0"),
            db_schema_version=int(data.get("db_schema_version", 1) or 1),
            download_url=data.get("download_url", ""),
            installer_url=data.get("installer_url", ""),
            sha256=data.get("sha256", ""),
            signature=data.get("signature", ""),
            mandatory=bool(data.get("mandatory", False)),
            release_date=data.get("release_date", ""),
            notes=list(data.get("notes", [])),
        )
