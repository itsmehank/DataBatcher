from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.dependencies import require_editor
from ..common import category_expr, parse_date, parse_region_key
from ..db import execute_write, fetch_all, normalize_row
from ..query_maps import get_region_tables

router = APIRouter()


class ListTypeUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    region: str
    date: str
    market: str
    symbol: str
    list_type: Literal["focus", "action", "pass"] | None


class ListViewItemUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    region: str
    date: str
    market: str
    symbol: str
    trigger_price: float | None = None
    stop_price: float | None = None
    status_tag: Literal["A", "B", "C", "D", "E"] | None = None
    memo: str | None = None


def _ensure_minervini_exists(region: str, date_value: str, market: str, symbol: str) -> None:
    tables = get_region_tables(region)
    sql = f"""
    SELECT 1 AS ok
    FROM {tables['minervini']}
    WHERE date = :date_value
      AND BINARY market = BINARY :market
      AND BINARY symbol = BINARY :symbol
    LIMIT 1
    """
    rows = fetch_all(sql, {"date_value": date_value, "market": market, "symbol": symbol})
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Symbol not present in Minervini results for given region/date/market",
        )


@router.get("/api/minervini")
def get_minervini(
    region: str = Query("US"),
    date_value: str = Query(..., alias="date"),
    market: str = Query(...),
    list_category: str = Query("all", alias="listCategory"),
) -> list[dict[str, Any]]:
    region_key = parse_region_key(region)
    allowed = {"focus", "action", "pass", "all"}
    if list_category not in allowed:
        raise HTTPException(status_code=400, detail="Invalid listCategory")

    tables = get_region_tables(region_key)
    where_category = "" if list_category == "all" else "AND ls.list_type = :list_type"
    sql = f"""
    SELECT
      m.symbol AS ticker,
      sm.name AS name,
      m.market AS market,
      sm.sector AS sector,
      m.rs_rating AS rs_rating,
      m.is_blue_dot AS is_blue_dot,
      {category_expr('sm.name')} AS category_val,
      ls.list_type AS list_type
    FROM {tables['minervini']} m
    LEFT JOIN {tables['symbol_master']} sm ON m.symbol = sm.symbol
    LEFT JOIN minervini_list_selection ls
      ON BINARY ls.region = BINARY :region_key
     AND ls.date = m.date
     AND BINARY ls.market = BINARY m.market
     AND BINARY ls.symbol = BINARY m.symbol
    WHERE m.date = :date_value AND BINARY m.market = BINARY :market
      {where_category}
    ORDER BY m.rs_rating DESC
    """
    rows = fetch_all(
        sql,
        {
            "date_value": date_value,
            "market": market,
            "region_key": region_key,
            "list_type": list_category,
        },
    )
    return normalize_row(rows)


@router.post("/api/minervini/list-type")
def update_minervini_list_type(
    payload: ListTypeUpdateRequest,
    _user: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    region_key = parse_region_key(payload.region)
    parsed_date = parse_date(payload.date, datetime.now(UTC).date())
    _ensure_minervini_exists(region_key, parsed_date, payload.market, payload.symbol)

    key_params = {
        "region": region_key,
        "date_value": parsed_date,
        "market": payload.market,
        "symbol": payload.symbol,
    }

    if payload.list_type is None:
        execute_write(
            """
            DELETE FROM minervini_list_selection
            WHERE BINARY region = BINARY :region
              AND date = :date_value
              AND BINARY market = BINARY :market
              AND BINARY symbol = BINARY :symbol
            """,
            key_params,
        )
        return {"ok": True, "action": "delete"}

    execute_write(
        """
        INSERT INTO minervini_list_selection (region, date, market, symbol, list_type)
        VALUES (:region, :date_value, :market, :symbol, :list_type)
        ON DUPLICATE KEY UPDATE
          list_type = VALUES(list_type),
          updated_at = CURRENT_TIMESTAMP
        """,
        {**key_params, "list_type": payload.list_type},
    )
    return {"ok": True, "action": "upsert"}


@router.get("/api/list-view/dates")
def get_list_view_dates(region: str = Query("US")) -> list[str]:
    region_key = parse_region_key(region)
    tables = get_region_tables(region_key)
    rows = fetch_all(
        f"""
        SELECT DISTINCT DATE_FORMAT(date, '%Y-%m-%d') AS value
        FROM {tables['minervini']}
        ORDER BY value DESC
        LIMIT 730
        """
    )
    return [row["value"] for row in rows]


@router.get("/api/list-view/items")
def get_list_view_items(
    region: str = Query("US"),
    date_value: str = Query(..., alias="date"),
    list_category: str = Query("all", alias="listCategory"),
) -> list[dict[str, Any]]:
    region_key = parse_region_key(region)
    parsed_date = parse_date(date_value, datetime.now(UTC).date())
    tables = get_region_tables(region_key)

    allowed = {"focus", "action", "pass", "all"}
    if list_category not in allowed:
        raise HTTPException(status_code=400, detail="Invalid listCategory")

    where_category = "" if list_category == "all" else "AND s.list_type = :list_type"
    rows = fetch_all(
        f"""
        SELECT
          s.symbol,
          sm.name,
          s.market,
          s.list_type,
          sm.sector,
          m.rs_rating,
          s.trigger_price,
          s.stop_price,
          s.status_tag,
          s.memo
        FROM minervini_list_selection s
        INNER JOIN {tables['minervini']} m
          ON BINARY m.symbol = BINARY s.symbol
         AND BINARY m.market = BINARY s.market
         AND m.date = s.date
        LEFT JOIN {tables['symbol_master']} sm
          ON BINARY sm.symbol = BINARY s.symbol
        WHERE BINARY s.region = BINARY :region
          AND s.date = :date_value
          {where_category}
        ORDER BY s.market, s.symbol
        """,
        {
            "region": region_key,
            "date_value": parsed_date,
            "list_type": list_category,
        },
    )
    return normalize_row(rows)


@router.patch("/api/list-view/item")
def update_list_view_item(
    payload: ListViewItemUpdateRequest,
    _user: dict[str, Any] = Depends(require_editor),
) -> dict[str, Any]:
    region_key = parse_region_key(payload.region)
    parsed_date = parse_date(payload.date, datetime.now(UTC).date())

    editable_fields = {"trigger_price", "stop_price", "status_tag", "memo"}
    fields_to_update = payload.model_fields_set.intersection(editable_fields)
    if not fields_to_update:
        raise HTTPException(status_code=400, detail="No editable fields provided")

    key_params: dict[str, Any] = {
        "region": region_key,
        "date_value": parsed_date,
        "market": payload.market,
        "symbol": payload.symbol,
    }

    exists_rows = fetch_all(
        """
        SELECT 1 AS ok
        FROM minervini_list_selection
        WHERE BINARY region = BINARY :region
          AND date = :date_value
          AND BINARY market = BINARY :market
          AND BINARY symbol = BINARY :symbol
        LIMIT 1
        """,
        key_params,
    )
    if not exists_rows:
        raise HTTPException(status_code=404, detail="Selection row not found")

    assignments: list[str] = []

    if "trigger_price" in fields_to_update:
        if payload.trigger_price is not None and payload.trigger_price < 0:
            raise HTTPException(status_code=400, detail="trigger_price must be >= 0")
        assignments.append("trigger_price = :trigger_price")
        key_params["trigger_price"] = payload.trigger_price

    if "stop_price" in fields_to_update:
        if payload.stop_price is not None and payload.stop_price < 0:
            raise HTTPException(status_code=400, detail="stop_price must be >= 0")
        assignments.append("stop_price = :stop_price")
        key_params["stop_price"] = payload.stop_price

    if "status_tag" in fields_to_update:
        assignments.append("status_tag = :status_tag")
        key_params["status_tag"] = payload.status_tag

    if "memo" in fields_to_update:
        memo_value = payload.memo.strip() if isinstance(payload.memo, str) else payload.memo
        if memo_value == "":
            memo_value = None
        if memo_value is not None and len(memo_value) > 1000:
            raise HTTPException(status_code=400, detail="memo must be <= 1000 chars")
        assignments.append("memo = :memo")
        key_params["memo"] = memo_value

    if not assignments:
        return {"ok": True, "action": "noop"}

    execute_write(
        f"""
        UPDATE minervini_list_selection
        SET {', '.join(assignments)},
            updated_at = CURRENT_TIMESTAMP
        WHERE BINARY region = BINARY :region
          AND date = :date_value
          AND BINARY market = BINARY :market
          AND BINARY symbol = BINARY :symbol
        """,
        key_params,
    )

    return {"ok": True, "action": "update"}
