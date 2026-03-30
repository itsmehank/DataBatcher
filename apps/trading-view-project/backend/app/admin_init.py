from __future__ import annotations

import logging
import os
from typing import Any

from .auth.password import hash_password, verify_password
from .db import execute_write, fetch_all

logger = logging.getLogger(__name__)

EDITOR_ROLE = "editor"


def _read_admin_credentials() -> tuple[str | None, str | None]:
    username = os.getenv("ADMIN_USERNAME", "").strip() or None
    password = os.getenv("ADMIN_PASSWORD", "") or None
    return username, password


def _password_matches(plain_password: str, password_hash: Any) -> bool:
    if not isinstance(password_hash, str) or not password_hash:
        return False

    try:
        return verify_password(plain_password, password_hash)
    except Exception:
        return False


def _create_admin_user(username: str, password: str) -> None:
    execute_write(
        """
        INSERT INTO users (username, password_hash, role, is_active, password_changed_at)
        VALUES (:username, :password_hash, :role, 1, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE id = id
        """,
        {
            "username": username,
            "password_hash": hash_password(password),
            "role": EDITOR_ROLE,
        },
    )


def _update_existing_admin(existing_user: dict[str, Any], password: str) -> str:
    password_changed = not _password_matches(password, existing_user.get("password_hash"))
    role_changed = existing_user.get("role") != EDITOR_ROLE
    inactive = not bool(existing_user.get("is_active"))

    if not any((password_changed, role_changed, inactive)):
        return "noop"

    assignments = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"user_id": existing_user["id"]}

    if password_changed:
        assignments.extend(
            [
                "password_hash = :password_hash",
                "password_changed_at = CURRENT_TIMESTAMP",
                "failed_login_count = 0",
                "locked_until = NULL",
            ]
        )
        params["password_hash"] = hash_password(password)

    if role_changed:
        assignments.append("role = :role")
        params["role"] = EDITOR_ROLE

    if inactive:
        assignments.append("is_active = 1")

    execute_write(
        f"""
        UPDATE users
        SET {', '.join(assignments)}
        WHERE id = :user_id
        """,
        params,
    )
    return "updated"


def ensure_admin_user_exists() -> str:
    username, password = _read_admin_credentials()
    if username is None and password is None:
        return "skipped"

    if username is None or password is None:
        logger.warning(
            "ADMIN_USERNAME and ADMIN_PASSWORD must both be set. Skipping admin bootstrap."
        )
        return "skipped_partial_env"

    rows = fetch_all(
        """
        SELECT id, username, password_hash, role, is_active, failed_login_count, locked_until
        FROM users
        WHERE username = :username
        LIMIT 1
        """,
        {"username": username},
    )

    if not rows:
        _create_admin_user(username, password)
        logger.info("Startup admin user '%s' created.", username)
        return "created"

    status = _update_existing_admin(rows[0], password)
    if status == "updated":
        logger.info("Startup admin user '%s' updated.", username)
    return status
