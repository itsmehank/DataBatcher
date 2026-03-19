from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.auth.cookie import COOKIE_NAME
from app.auth.password import hash_password
from app.auth.token import ALGORITHM, create_access_token
from app.config import settings
from app.routers import auth


def test_login_success_sets_cookie(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "fetch_all",
        lambda sql, params=None: [
            {
                "id": 1,
                "username": "admin",
                "password_hash": hash_password("pw-123"),
                "role": "editor",
                "is_active": 1,
                "failed_login_count": 0,
                "locked_until": None,
            }
        ],
    )
    monkeypatch.setattr(auth, "execute_write", lambda sql, params=None: 1)

    response = client.post("/api/auth/login", json={"username": "admin", "password": "pw-123"})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "username": "admin", "role": "editor"}
    set_cookie = response.headers.get("set-cookie", "")
    assert f"{COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_wrong_password_returns_401(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "fetch_all",
        lambda sql, params=None: [
            {
                "id": 1,
                "username": "admin",
                "password_hash": hash_password("right-password"),
                "role": "editor",
                "is_active": 1,
                "failed_login_count": 0,
                "locked_until": None,
            }
        ],
    )
    called = {"count": 0}

    def fake_execute_write(sql: str, params=None) -> int:
        called["count"] += 1
        return 1

    monkeypatch.setattr(auth, "execute_write", fake_execute_write)

    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
    assert called["count"] == 1


def test_login_nonexistent_user_returns_401(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(auth, "fetch_all", lambda sql, params=None: [])

    response = client.post("/api/auth/login", json={"username": "ghost", "password": "pw"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_inactive_user_returns_403(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "fetch_all",
        lambda sql, params=None: [
            {
                "id": 1,
                "username": "admin",
                "password_hash": hash_password("pw"),
                "role": "editor",
                "is_active": 0,
                "failed_login_count": 0,
                "locked_until": None,
            }
        ],
    )

    response = client.post("/api/auth/login", json={"username": "admin", "password": "pw"})

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


def test_login_locked_user_returns_403(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "fetch_all",
        lambda sql, params=None: [
            {
                "id": 1,
                "username": "admin",
                "password_hash": hash_password("pw"),
                "role": "editor",
                "is_active": 1,
                "failed_login_count": 5,
                "locked_until": datetime.now(timezone.utc) + timedelta(minutes=10),
            }
        ],
    )

    response = client.post("/api/auth/login", json={"username": "admin", "password": "pw"})

    assert response.status_code == 403
    assert response.json()["detail"] == "User is temporarily locked"


def test_logout_clears_cookie(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, create_access_token(subject="alice", role="editor"))

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    set_cookie = response.headers.get("set-cookie", "")
    assert "Max-Age=0" in set_cookie


def test_me_without_cookie_returns_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_me_with_valid_cookie_returns_user_info(client: TestClient) -> None:
    token = create_access_token(subject="viewer-a", role="viewer")
    client.cookies.set(COOKIE_NAME, token)

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "username": "viewer-a",
        "role": "viewer",
    }


def test_me_with_expired_cookie_returns_unauthenticated(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": "viewer-a",
            "role": "viewer",
            "type": "access",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    client.cookies.set(COOKIE_NAME, expired)

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_login_rate_limit_blocks_after_5_attempts(client: TestClient, monkeypatch) -> None:
    from app.rate_limit import _login_attempts

    _login_attempts.clear()
    monkeypatch.setattr(auth, "fetch_all", lambda sql, params=None: [])

    for _ in range(5):
        response = client.post("/api/auth/login", json={"username": "x", "password": "x"})
        assert response.status_code == 401

    response = client.post("/api/auth/login", json={"username": "x", "password": "x"})
    assert response.status_code == 429
    assert "Too many" in response.json()["detail"]

    _login_attempts.clear()
