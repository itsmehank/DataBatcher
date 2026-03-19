from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from ..config import settings

ALGORITHM = "HS256"


def _require_secret_key() -> str:
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is required")
    return settings.secret_key


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, _require_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, _require_secret_key(), algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload
