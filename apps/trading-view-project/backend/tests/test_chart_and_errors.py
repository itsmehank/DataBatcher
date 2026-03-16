from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.routers import chart, options


def test_daily_chart_payload_shape(client: TestClient, monkeypatch) -> None:
    def fake_fetch_all(sql: str, params=None):
        if "base.rs_line AS value" in sql:
            return [{"time": "2026-03-01", "value": 1.2345}]
        return [
            {
                "time": "2026-03-01",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1200,
                "sma_50": 10.1,
                "sma_100": 9.8,
                "sma_150": 9.3,
                "sma_200": 8.7,
                "rs_line": 1.1,
                "volume_sma_50": 1000,
            }
        ]

    monkeypatch.setattr(chart, "fetch_all", fake_fetch_all)

    response = client.get(
        "/api/chart/daily",
        params={"region": "US", "symbol": "AAPL", "from": "2026-02-01", "to": "2026-03-01"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1D"
    assert len(body["candles"]) == 1
    assert len(body["volume"]) == 1
    assert "rs_line" in body["indicators"]
    assert body["meta"]["rs_1y_high"] == {"time": "2026-03-01", "value": 1.2345}


def test_benchmark_chart_label_kr(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(chart, "fetch_all", lambda sql, params=None: [{"time": "2026-03-01", "value": 2500.0}])

    response = client.get(
        "/api/chart/benchmark-daily",
        params={"region": "KR", "from": "2026-02-01", "to": "2026-03-01"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "1001"
    assert body["meta"]["benchmark_label"] == "KOSPI"
    assert body["indicators"]["benchmark_close"] == [{"time": "2026-03-01", "value": 2500.0}]


def test_invalid_list_category_returns_400(client: TestClient) -> None:
    response = client.get(
        "/api/list-view/items",
        params={"region": "US", "date": "2026-03-01", "listCategory": "invalid"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid listCategory"


def test_sqlalchemy_error_is_mapped_to_500(client: TestClient, monkeypatch) -> None:
    def boom(sql: str, params=None):
        raise SQLAlchemyError("db exploded")

    monkeypatch.setattr(options, "fetch_all", boom)

    response = client.get("/api/options/dates", params={"region": "US"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error"}


def test_health_db_success(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(options, "fetch_all", lambda sql, params=None: [{"ok": 1}])

    response = client.get("/api/health/db", params={"region": "US"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["region"] == "US"
    assert "us_symbol_master" in body["checked"]


def test_health_db_missing_object_returns_503(client: TestClient, monkeypatch) -> None:
    def selective_fail(sql: str, params=None):
        if params and params.get("table_name") == "us_symbol_master":
            return []
        return [{"ok": 1}]

    monkeypatch.setattr(options, "fetch_all", selective_fail)

    response = client.get("/api/health/db", params={"region": "US"})

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["message"] == "Required DB objects are missing"
    assert "us_symbol_master" in body["detail"]["objects"]
