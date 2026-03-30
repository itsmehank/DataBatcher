from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app import main as app_main


def test_startup_runs_admin_bootstrap_when_db_check_enabled(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app_main.settings, "startup_db_check", True)
    monkeypatch.setattr(app_main, "verify_db_connection", lambda: calls.append("db"))
    monkeypatch.setattr(
        app_main,
        "ensure_admin_user_exists",
        lambda: calls.append("bootstrap") or "created",
    )

    with TestClient(app_main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == ["db", "bootstrap"]


def test_startup_skips_admin_bootstrap_when_db_check_disabled(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(app_main.settings, "startup_db_check", False)
    monkeypatch.setattr(app_main, "verify_db_connection", lambda: calls.append("db"))
    monkeypatch.setattr(app_main, "ensure_admin_user_exists", lambda: calls.append("bootstrap"))

    with TestClient(app_main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == []


def test_startup_keeps_public_health_alive_when_bootstrap_fails(monkeypatch, caplog) -> None:
    monkeypatch.setattr(app_main.settings, "startup_db_check", True)
    monkeypatch.setattr(app_main, "verify_db_connection", lambda: None)

    def fail_bootstrap() -> str:
        raise RuntimeError("bootstrap failed")

    monkeypatch.setattr(app_main, "ensure_admin_user_exists", fail_bootstrap)
    caplog.set_level(logging.WARNING)

    with TestClient(app_main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "Admin bootstrap skipped due to startup error: bootstrap failed" in caplog.text
