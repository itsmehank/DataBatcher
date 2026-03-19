from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..auth.cookie import delete_auth_cookie, set_auth_cookie
from ..auth.dependencies import get_current_user
from ..auth.password import verify_password
from ..auth.token import create_access_token
from ..db import execute_write, fetch_all
from ..rate_limit import check_login_rate_limit

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    model_config = {"extra": "forbid"}

    username: str
    password: str


def _parse_locked_until(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _is_locked(locked_until_value: Any) -> bool:
    locked_until = _parse_locked_until(locked_until_value)
    if locked_until is None:
        return False

    now = datetime.now(timezone.utc)
    if locked_until.tzinfo is None:
        return locked_until > now.replace(tzinfo=None)
    return locked_until > now


@router.post("/api/auth/login", dependencies=[Depends(check_login_rate_limit)])
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT id, username, password_hash, role, is_active, failed_login_count, locked_until
        FROM users WHERE username = :username LIMIT 1
        """,
        {"username": payload.username},
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = rows[0]
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="User is inactive")

    if _is_locked(user.get("locked_until")):
        raise HTTPException(status_code=403, detail="User is temporarily locked")

    password_hash = user.get("password_hash")
    if not isinstance(password_hash, str) or not verify_password(payload.password, password_hash):
        execute_write(
            """
            UPDATE users SET failed_login_count = failed_login_count + 1,
              locked_until = CASE WHEN failed_login_count >= 4 THEN DATE_ADD(NOW(), INTERVAL 15 MINUTE) ELSE locked_until END
            WHERE id = :user_id
            """,
            {"user_id": user["id"]},
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    execute_write(
        """
        UPDATE users SET last_login_at = CURRENT_TIMESTAMP, failed_login_count = 0 WHERE id = :user_id
        """,
        {"user_id": user["id"]},
    )

    username = str(user["username"])
    role = str(user["role"])
    token = create_access_token(subject=username, role=role)
    set_auth_cookie(response, token)
    return {"ok": True, "username": username, "role": role}


@router.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    delete_auth_cookie(response)
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "username": user["username"], "role": user["role"]}
