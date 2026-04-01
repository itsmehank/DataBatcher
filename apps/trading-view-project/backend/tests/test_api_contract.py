from __future__ import annotations

from fastapi.testclient import TestClient

from app.routers import minervini, options


def test_get_dates_returns_values(client: TestClient, monkeypatch) -> None:
    def fake_fetch_all(sql: str, params=None):
        return [{"value": "2026-03-13"}, {"value": "2026-03-12"}]

    monkeypatch.setattr(options, "fetch_all", fake_fetch_all)

    response = client.get("/api/options/dates", params={"region": "US"})

    assert response.status_code == 200
    assert response.json() == ["2026-03-13", "2026-03-12"]


def test_get_symbol_options_returns_symbol_name_pairs(client: TestClient, monkeypatch) -> None:
    def fake_fetch_all(sql: str, params=None):
        return [{"symbol": "AAPL", "name": "Apple Inc."}, {"symbol": "MSFT", "name": "Microsoft Corp."}]

    monkeypatch.setattr(options, "fetch_all", fake_fetch_all)

    response = client.get(
        "/api/symbol-options",
        params={"region": "US", "market": "NASDAQ", "category": "A"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corp."},
    ]


def test_invalid_region_returns_400(client: TestClient) -> None:
    response = client.get("/api/options/dates", params={"region": "INVALID"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid region"


def test_update_list_view_item_rejects_empty_patch(editor_cookie: TestClient) -> None:
    response = editor_cookie.patch(
        "/api/list-view/item",
        json={
            "region": "US",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No editable fields provided"


def test_update_minervini_list_type_delete_path(editor_cookie: TestClient, monkeypatch) -> None:
    called: dict[str, object] = {}

    monkeypatch.setattr(minervini, "_ensure_minervini_exists", lambda *args, **kwargs: None)

    def fake_execute_write(sql: str, params=None):
        called["params"] = params
        return 1

    monkeypatch.setattr(minervini, "execute_write", fake_execute_write)

    response = editor_cookie.post(
        "/api/minervini/list-type",
        json={
            "region": "us",
            "date": "2026-03-13",
            "market": "NASDAQ",
            "symbol": "AAPL",
            "list_type": None,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "action": "delete"}
    assert called["params"] == {
        "region": "US",
        "date_value": "2026-03-13",
        "market": "NASDAQ",
        "symbol": "AAPL",
    }


def test_get_minervini_accepts_list_category_filter(client: TestClient, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_fetch_all(sql: str, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(minervini, "fetch_all", fake_fetch_all)

    response = client.get(
        "/api/minervini",
        params={"region": "US", "date": "2026-03-13", "market": "NASDAQ", "listCategory": "focus"},
    )

    assert response.status_code == 200
    assert "AND ls.list_type = :list_type" in str(captured["sql"])
    assert captured["params"] == {
        "date_value": "2026-03-13",
        "market": "NASDAQ",
        "region_key": "US",
        "list_type": "focus",
    }


def test_get_minervini_rejects_invalid_list_category(client: TestClient) -> None:
    response = client.get(
        "/api/minervini",
        params={"region": "US", "date": "2026-03-13", "market": "NASDAQ", "listCategory": "invalid"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid listCategory"
