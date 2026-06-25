"""Valida endpoints públicos do servidor de licenças.

Uso:
    python scripts/check_deploy.py https://boxio-license-server.onrender.com
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def fetch_json(url: str, timeout: int = 20) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"message": str(exc)}
        return exc.code, payload


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/check_deploy.py https://boxio-license-server.onrender.com")
        return 1

    base_url = sys.argv[1].strip().rstrip("/")
    if not base_url.startswith("https://") and not base_url.startswith("http://"):
        print("Informe a URL completa, começando com https://")
        return 1

    ok = True
    for path in ["/health", "/health/db"]:
        url = f"{base_url}{path}"
        status, payload = fetch_json(url)
        passed = 200 <= status < 300 and payload.get("ok") is True
        ok = ok and passed
        marker = "OK" if passed else "FALHOU"
        print(f"[{marker}] {url} -> HTTP {status}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
