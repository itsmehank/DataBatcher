from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

from ..common import parse_date, parse_region_key
from ..db import fetch_all, normalize_row
from ..query_maps import get_region_tables

router = APIRouter()


def _daily_chart_sql(view_name: str) -> str:
    return f"""
    SELECT
      DATE_FORMAT(raw_date, '%Y-%m-%d') AS time,
      open,
      high,
      low,
      close,
      volume,
      sma_50,
      sma_100,
      sma_150,
      sma_200,
      rs_line,
      volume_sma_50
    FROM (
      SELECT
        date AS raw_date,
        open,
        high,
        low,
        close,
        volume,
        sma_50,
        sma_100,
        sma_150,
        sma_200,
        rs_line,
        AVG(volume) OVER (
          PARTITION BY symbol
          ORDER BY date
          ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) AS volume_sma_50
      FROM {view_name}
      WHERE symbol = :symbol
        AND date >= DATE_SUB(:from_date, INTERVAL 49 DAY)
        AND date <= :to_date
    ) base
    WHERE raw_date >= :from_date
      AND raw_date <= :to_date
    ORDER BY raw_date
    """


def _weekly_chart_sql(view_name: str) -> str:
    return f"""
    SELECT
      DATE_FORMAT(raw_week_start, '%Y-%m-%d') AS time,
      open,
      high,
      low,
      close,
      volume,
      sma_10,
      sma_20,
      sma_50,
      sma_100,
      sma_200,
      ema_21,
      volume_sma_10
    FROM (
      SELECT
        week_start AS raw_week_start,
        open,
        high,
        low,
        close,
        volume,
        AVG(close) OVER (
          PARTITION BY symbol
          ORDER BY week_start
          ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS sma_10,
        sma_20,
        sma_50,
        sma_100,
        sma_200,
        ema_21,
        AVG(volume) OVER (
          PARTITION BY symbol
          ORDER BY week_start
          ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS volume_sma_10
      FROM {view_name}
      WHERE symbol = :symbol
        AND week_start >= DATE_SUB(:from_date, INTERVAL 9 WEEK)
        AND week_start <= :to_date
    ) base
    WHERE raw_week_start >= :from_date
      AND raw_week_start <= :to_date
    ORDER BY raw_week_start
    """


def _build_chart_payload(rows: list[dict[str, Any]], indicator_keys: list[str]) -> dict[str, Any]:
    candles: list[dict[str, Any]] = []
    volume: list[dict[str, Any]] = []
    indicators: dict[str, list[dict[str, Any]]] = {k: [] for k in indicator_keys}

    for row in rows:
        time = row["time"]
        open_price = row["open"]
        close_price = row["close"]

        candles.append(
            {
                "time": time,
                "open": open_price,
                "high": row["high"],
                "low": row["low"],
                "close": close_price,
            }
        )

        if row.get("volume") is not None:
            volume.append(
                {
                    "time": time,
                    "value": row["volume"],
                    "color": "rgba(34, 197, 94, 0.45)" if close_price >= open_price else "rgba(239, 68, 68, 0.45)",
                }
            )

        for key in indicator_keys:
            val = row.get(key)
            if val is not None:
                indicators[key].append({"time": time, "value": val})

    return {"candles": candles, "volume": volume, "indicators": indicators}


def _daily_rs_1y_high(view_name: str, symbol: str) -> dict[str, Any] | None:
    sql = f"""
    SELECT
      DATE_FORMAT(base.date, '%Y-%m-%d') AS time,
      base.rs_line AS value
    FROM {view_name} base
    WHERE base.symbol = :symbol
      AND base.rs_line IS NOT NULL
      AND base.date >= DATE_SUB(
        (
          SELECT MAX(v2.date)
          FROM {view_name} v2
          WHERE v2.symbol = :symbol
        ),
        INTERVAL 365 DAY
      )
    ORDER BY base.rs_line DESC, base.date DESC
    LIMIT 1
    """
    rows = fetch_all(sql, {"symbol": symbol})
    if not rows:
        return None
    row = normalize_row(rows[0])
    if row.get("time") is None or row.get("value") is None:
        return None
    return {"time": row["time"], "value": row["value"]}


def _benchmark_symbol(region: str) -> str:
    key = parse_region_key(region)
    if key == "KR":
        return "1001"
    return "US500"


@router.get("/api/chart/daily")
def get_daily_chart(
    region: str = Query("US"),
    symbol: str = Query(...),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
) -> dict[str, Any]:
    tables = get_region_tables(region)
    end_default = datetime.now(UTC).date()
    start_default = end_default - timedelta(days=180)
    parsed_from = parse_date(from_date, start_default)
    parsed_to = parse_date(to_date, end_default)

    rows = fetch_all(
        _daily_chart_sql(tables["daily_view"]),
        {"symbol": symbol, "from_date": parsed_from, "to_date": parsed_to},
    )

    normalized = normalize_row(rows)
    payload = _build_chart_payload(
        normalized,
        ["sma_50", "sma_100", "sma_150", "sma_200", "rs_line", "volume_sma_50"],
    )
    payload["meta"] = {
        "rs_1y_high": _daily_rs_1y_high(tables["daily_view"], symbol),
    }
    payload.update({"symbol": symbol, "timeframe": "1D", "from": parsed_from, "to": parsed_to})
    return payload


@router.get("/api/chart/benchmark-daily")
def get_benchmark_daily_chart(
    region: str = Query("US"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
) -> dict[str, Any]:
    region_key = parse_region_key(region)
    tables = get_region_tables(region_key)
    symbol = _benchmark_symbol(region_key)

    end_default = datetime.now(UTC).date()
    start_default = end_default - timedelta(days=180)
    parsed_from = parse_date(from_date, start_default)
    parsed_to = parse_date(to_date, end_default)

    rows = fetch_all(
        f"""
        SELECT
          DATE_FORMAT(date, '%Y-%m-%d') AS time,
          close AS value
        FROM {tables['index_daily']}
        WHERE symbol = :symbol
          AND date >= :from_date
          AND date <= :to_date
          AND close IS NOT NULL
        ORDER BY date
        """,
        {"symbol": symbol, "from_date": parsed_from, "to_date": parsed_to},
    )

    normalized_rows = normalize_row(rows)
    benchmark_line = [{"time": row["time"], "value": row["value"]} for row in normalized_rows]

    return {
        "symbol": symbol,
        "timeframe": "1D",
        "from": parsed_from,
        "to": parsed_to,
        "candles": [],
        "volume": [],
        "indicators": {"benchmark_close": benchmark_line},
        "meta": {"benchmark_label": "KOSPI" if region_key == "KR" else "S&P 500"},
    }


@router.get("/api/chart/weekly")
def get_weekly_chart(
    region: str = Query("US"),
    symbol: str = Query(...),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
) -> dict[str, Any]:
    tables = get_region_tables(region)
    end_default = datetime.now(UTC).date()
    start_default = end_default - timedelta(days=365 * 2)
    parsed_from = parse_date(from_date, start_default)
    parsed_to = parse_date(to_date, end_default)

    rows = fetch_all(
        _weekly_chart_sql(tables["weekly_view"]),
        {"symbol": symbol, "from_date": parsed_from, "to_date": parsed_to},
    )

    normalized = normalize_row(rows)
    payload = _build_chart_payload(
        normalized,
        ["sma_10", "sma_20", "sma_50", "sma_100", "sma_200", "ema_21", "volume_sma_10"],
    )
    payload.update({"symbol": symbol, "timeframe": "1W", "from": parsed_from, "to": parsed_to})
    return payload
