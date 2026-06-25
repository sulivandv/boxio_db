"""Validação de integridade dos pacotes de atualização."""
from __future__ import annotations

import hashlib
from pathlib import Path


def calculate_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_sha256(path: Path, expected_hash: str) -> None:
    """Interrompe a atualização quando o hash não bate com o manifesto."""
    if not expected_hash:
        raise ValueError("Manifesto sem SHA-256. A atualização foi bloqueada por segurança.")
    actual_hash = calculate_sha256(path)
    if actual_hash.lower() != expected_hash.lower():
        raise ValueError("Arquivo de atualização corrompido ou modificado. SHA-256 inválido.")
