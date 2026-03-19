from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from app.auth.password import hash_password, verify_password
from app.auth.token import ALGORITHM, create_access_token, decode_access_token
from app.config import settings


def test_hash_and_verify_password_roundtrip() -> None:
    hashed = hash_password("my-password")
    assert hashed != "my-password"
    assert verify_password("my-password", hashed) is True


def test_verify_password_wrong_input() -> None:
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_token_roundtrip() -> None:
    token = create_access_token(subject="alice", role="editor")
    payload = decode_access_token(token)

    assert payload["sub"] == "alice"
    assert payload["role"] == "editor"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_token_expired_raises() -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "alice",
            "role": "editor",
            "type": "access",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    with pytest.raises(JWTError):
        decode_access_token(token)


def test_decode_token_invalid_raises() -> None:
    with pytest.raises(JWTError):
        decode_access_token("not-a-valid-token")
