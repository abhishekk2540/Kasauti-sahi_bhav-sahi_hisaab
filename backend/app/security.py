import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import get_settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def create_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        if data.get("purpose"):  # password-reset (or other special-purpose) tokens are not login tokens
            return None
        return int(data["sub"])
    except Exception:
        return None


RESET_TOKEN_MINUTES = 30


def _pwd_fingerprint(stored_hash: str | None) -> str:
    return hashlib.sha256((stored_hash or "").encode()).hexdigest()[:16]


def create_reset_token(user_id: int, password_hash: str | None) -> str:
    """Short-lived, stateless reset token. It embeds a fingerprint of the current password hash,
    so it stops working as soon as the password is changed (single use)."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
    payload = {"sub": str(user_id), "purpose": "reset", "pwd": _pwd_fingerprint(password_hash), "exp": expires}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def decode_reset_token(token: str) -> tuple[int, str] | None:
    """Returns (user_id, password fingerprint) for a valid reset token, else None."""
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        if data.get("purpose") != "reset":
            return None
        return int(data["sub"]), str(data["pwd"])
    except Exception:
        return None


def reset_token_matches(fingerprint: str, password_hash: str | None) -> bool:
    return hmac.compare_digest(fingerprint, _pwd_fingerprint(password_hash))