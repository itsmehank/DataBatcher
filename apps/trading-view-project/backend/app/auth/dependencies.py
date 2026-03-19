from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from jose import JWTError

from .cookie import COOKIE_NAME
from .token import decode_access_token


def get_current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    username = payload.get("sub")
    role = payload.get("role")
    if not isinstance(username, str) or not username:
        return None
    if not isinstance(role, str) or not role:
        return None
    return {"username": username, "role": role}


def require_authenticated(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_editor(request: Request) -> dict[str, Any]:
    user = require_authenticated(request)
    if user.get("role") != "editor":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user
