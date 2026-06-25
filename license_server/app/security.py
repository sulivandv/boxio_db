from __future__ import annotations

import hashlib
import hmac
import secrets
from app.config import get_settings


def create_activation_token(license_key: str, activation_id: str, fingerprint: str) -> str:
    """Gera token assinado para uma ativação específica."""
    secret = get_settings().token_secret or "dev-secret"
    nonce = secrets.token_hex(16)
    payload = f"{license_key}|{activation_id}|{fingerprint}|{nonce}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_activation_token(token: str, license_key: str, activation_id: str, fingerprint: str) -> bool:
    try:
        secret = get_settings().token_secret or "dev-secret"
        parts = token.split("|")
        if len(parts) != 5:
            return False
        lk, aid, fp, nonce, signature = parts
        if lk != license_key or aid != activation_id or fp != fingerprint:
            return False
        payload = f"{lk}|{aid}|{fp}|{nonce}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False
