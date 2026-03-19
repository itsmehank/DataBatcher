from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "mysql+pymysql://test_user:test_password@127.0.0.1:3306/test_db?charset=utf8mb4",
)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("STARTUP_DB_CHECK", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.auth.cookie import COOKIE_NAME
from app.auth.token import create_access_token


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def editor_cookie(client: TestClient) -> TestClient:
    token = create_access_token(subject="editor_user", role="editor")
    client.cookies.set(COOKIE_NAME, token)
    return client


@pytest.fixture
def viewer_cookie(client: TestClient) -> TestClient:
    token = create_access_token(subject="viewer_user", role="viewer")
    client.cookies.set(COOKIE_NAME, token)
    return client
