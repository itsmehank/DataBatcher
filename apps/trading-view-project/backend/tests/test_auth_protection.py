from __future__ import annotations

from fastapi.testclient import TestClient

from app.routers import minervini


def test_post_list_type_without_cookie_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/minervini/list-type",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "list_type": "focus",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_post_list_type_with_viewer_cookie_returns_403(viewer_cookie: TestClient) -> None:
    response = viewer_cookie.post(
        "/api/minervini/list-type",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "list_type": "focus",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_post_list_type_with_editor_cookie_returns_200(editor_cookie: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(minervini, "_ensure_minervini_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(minervini, "execute_write", lambda sql, params=None: 1)

    response = editor_cookie.post(
        "/api/minervini/list-type",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "list_type": "focus",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "action": "upsert"}


def test_patch_list_view_item_without_cookie_returns_401(client: TestClient) -> None:
    response = client.patch(
        "/api/list-view/item",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "memo": "note",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_patch_list_view_item_with_viewer_cookie_returns_403(viewer_cookie: TestClient) -> None:
    response = viewer_cookie.patch(
        "/api/list-view/item",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "memo": "note",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_patch_list_view_item_with_editor_cookie_returns_200(
    editor_cookie: TestClient,
    monkeypatch,
) -> None:
    responses = [[{"ok": 1}]]

    def fake_fetch_all(sql: str, params=None):
        return responses.pop(0)

    monkeypatch.setattr(minervini, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(minervini, "execute_write", lambda sql, params=None: 1)

    response = editor_cookie.patch(
        "/api/list-view/item",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "memo": "updated memo",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "action": "update"}


def test_get_minervini_without_cookie_still_works(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(minervini, "fetch_all", lambda sql, params=None: [])

    response = client.get(
        "/api/minervini",
        params={"region": "US", "date": "2026-03-13", "market": "NASDAQ"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_list_view_items_without_cookie_still_works(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(minervini, "fetch_all", lambda sql, params=None: [])

    response = client.get(
        "/api/list-view/items",
        params={"region": "US", "date": "2026-03-13", "listCategory": "all"},
    )

    assert response.status_code == 200
    assert response.json() == []
