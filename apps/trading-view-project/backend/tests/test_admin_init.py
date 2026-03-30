from __future__ import annotations

import logging

import pytest

from app import admin_init


def test_ensure_admin_user_exists_skips_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(
        admin_init,
        "fetch_all",
        lambda *args, **kwargs: pytest.fail("fetch_all should not be called"),
    )

    assert admin_init.ensure_admin_user_exists() == "skipped"


def test_ensure_admin_user_exists_skips_on_partial_env(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    caplog.set_level(logging.WARNING)

    assert admin_init.ensure_admin_user_exists() == "skipped_partial_env"
    assert "ADMIN_USERNAME and ADMIN_PASSWORD must both be set" in caplog.text


def test_ensure_admin_user_exists_creates_missing_user(monkeypatch) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw-123")
    monkeypatch.setattr(admin_init, "fetch_all", lambda *args, **kwargs: [])
    monkeypatch.setattr(admin_init, "hash_password", lambda plain: f"HASH::{plain}")

    def fake_execute_write(sql: str, params=None) -> int:
        calls["sql"] = sql
        calls["params"] = params
        return 1

    monkeypatch.setattr(admin_init, "execute_write", fake_execute_write)

    assert admin_init.ensure_admin_user_exists() == "created"
    assert "INSERT INTO users" in str(calls["sql"])
    assert calls["params"] == {
        "username": "admin",
        "password_hash": "HASH::pw-123",
        "role": "editor",
    }


def test_ensure_admin_user_exists_is_noop_for_matching_active_editor(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw-123")
    monkeypatch.setattr(
        admin_init,
        "fetch_all",
        lambda *args, **kwargs: [
            {
                "id": 7,
                "username": "admin",
                "password_hash": "stored-hash",
                "role": "editor",
                "is_active": 1,
            }
        ],
    )
    monkeypatch.setattr(admin_init, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(
        admin_init,
        "execute_write",
        lambda *args, **kwargs: pytest.fail("execute_write should not be called"),
    )

    assert admin_init.ensure_admin_user_exists() == "noop"


def test_ensure_admin_user_exists_updates_password_and_resets_lock(monkeypatch) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "next-password")
    monkeypatch.setattr(
        admin_init,
        "fetch_all",
        lambda *args, **kwargs: [
            {
                "id": 7,
                "username": "admin",
                "password_hash": "stored-hash",
                "role": "editor",
                "is_active": 1,
            }
        ],
    )
    monkeypatch.setattr(admin_init, "verify_password", lambda plain, hashed: False)
    monkeypatch.setattr(admin_init, "hash_password", lambda plain: f"HASH::{plain}")

    def fake_execute_write(sql: str, params=None) -> int:
        calls["sql"] = sql
        calls["params"] = params
        return 1

    monkeypatch.setattr(admin_init, "execute_write", fake_execute_write)

    assert admin_init.ensure_admin_user_exists() == "updated"
    assert "failed_login_count = 0" in str(calls["sql"])
    assert "locked_until = NULL" in str(calls["sql"])
    assert calls["params"] == {"user_id": 7, "password_hash": "HASH::next-password"}


def test_ensure_admin_user_exists_updates_role_without_resetting_lock(monkeypatch) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw-123")
    monkeypatch.setattr(
        admin_init,
        "fetch_all",
        lambda *args, **kwargs: [
            {
                "id": 8,
                "username": "admin",
                "password_hash": "stored-hash",
                "role": "viewer",
                "is_active": 0,
            }
        ],
    )
    monkeypatch.setattr(admin_init, "verify_password", lambda plain, hashed: True)

    def fake_execute_write(sql: str, params=None) -> int:
        calls["sql"] = sql
        calls["params"] = params
        return 1

    monkeypatch.setattr(admin_init, "execute_write", fake_execute_write)

    assert admin_init.ensure_admin_user_exists() == "updated"
    assert "role = :role" in str(calls["sql"])
    assert "is_active = 1" in str(calls["sql"])
    assert "failed_login_count = 0" not in str(calls["sql"])
    assert "locked_until = NULL" not in str(calls["sql"])
    assert calls["params"] == {"user_id": 8, "role": "editor"}
