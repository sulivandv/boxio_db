"""Identificação estável do dispositivo para ativação de licença.

A identificação nunca envia dados sensíveis puros: as informações locais são
normalizadas e convertidas em hash SHA-256. Isso dificulta copiar o executável
para outra máquina mantendo a mesma licença local.
"""
from __future__ import annotations

import hashlib
import os
import platform
import socket
import uuid


def _windows_machine_guid() -> str:
    if platform.system().lower() != "windows":
        return ""
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except Exception:
        return ""


def raw_device_material() -> str:
    parts = [
        platform.system(),
        platform.release(),
        platform.version(),
        platform.machine(),
        socket.gethostname(),
        str(uuid.getnode()),
        os.environ.get("COMPUTERNAME", ""),
        os.environ.get("USERNAME", ""),
        _windows_machine_guid(),
    ]
    return "|".join(str(p or "").strip().lower() for p in parts)


def get_device_fingerprint() -> str:
    return hashlib.sha256(raw_device_material().encode("utf-8")).hexdigest()


def get_device_name() -> str:
    return socket.gethostname() or platform.node() or "Dispositivo"
