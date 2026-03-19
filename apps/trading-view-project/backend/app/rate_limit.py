from __future__ import annotations

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])

_login_attempts: dict[str, list[float]] = {}
_LOGIN_LIMIT = 5
_LOGIN_WINDOW_SECONDS = 60


def check_login_rate_limit(request: Request) -> None:
    import time

    ip = get_remote_address(request)
    now = time.monotonic()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]

    if len(attempts) >= _LOGIN_LIMIT:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    attempts.append(now)
    _login_attempts[ip] = attempts
