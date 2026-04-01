from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from ..common import category_expr, parse_region_key
from ..db import fetch_all
from ..query_maps import get_region_tables

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health/db")
def health_db(region: str = Query("US")) -> dict[str, object]:
    region_key = parse_region_key(region)
    tables = get_region_tables(region_key)
    objects = sorted(set(tables.values()))

    missing_objects: list[str] = []
    for object_name in objects:
        try:
            rows = fetch_all(
                """
                SELECT 1 AS ok
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
                LIMIT 1
                """,
                {"table_name": object_name},
            )
        except SQLAlchemyError:
            missing_objects.append(object_name)
            continue
        if not rows:
            missing_objects.append(object_name)

    if missing_objects:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Required DB objects are missing",
                "region": region_key,
                "objects": missing_objects,
            },
        )

    return {
        "status": "ok",
        "region": region_key,
        "checked": objects,
    }


@router.get("/api/options/dates")
def get_dates(region: str = Query("US")) -> list[str]:
    tables = get_region_tables(region)
    sql = f"""
    SELECT DISTINCT DATE_FORMAT(date, '%Y-%m-%d') AS value
    FROM {tables['price_daily']}
    ORDER BY value DESC
    LIMIT 730
    """
    rows = fetch_all(sql)
    return [row["value"] for row in rows]


@router.get("/api/options/markets")
def get_markets(region: str = Query("US")) -> list[str]:
    tables = get_region_tables(region)
    sql = f"""
    SELECT DISTINCT market AS value
    FROM {tables['symbol_master']}
    WHERE status = 'ACTIVE'
    ORDER BY value
    """
    rows = fetch_all(sql)
    return [row["value"] for row in rows]


@router.get("/api/options/categories")
def get_categories(region: str = Query("US"), market: str = Query(...)) -> list[str]:
    tables = get_region_tables(region)
    sql = f"""
    SELECT DISTINCT {category_expr('name')} AS value
    FROM {tables['symbol_master']}
    WHERE status = 'ACTIVE' AND market = :market
    ORDER BY value
    """
    rows = fetch_all(sql, {"market": market})
    return [row["value"] for row in rows]


@router.get("/api/symbols")
def get_symbols(
    region: str = Query("US"),
    market: str = Query(...),
    category: str = Query(...),
) -> list[str]:
    tables = get_region_tables(region)
    sql = f"""
    SELECT symbol AS value
    FROM {tables['symbol_master']}
    WHERE status = 'ACTIVE'
      AND market = :market
      AND ({category_expr('name')}) = :category
    ORDER BY name
    """
    rows = fetch_all(sql, {"market": market, "category": category})
    return [row["value"] for row in rows]


@router.get("/api/symbol-options")
def get_symbol_options(
    region: str = Query("US"),
    market: str = Query(...),
    category: str = Query(...),
) -> list[dict[str, str | None]]:
    tables = get_region_tables(region)
    sql = f"""
    SELECT symbol, name
    FROM {tables['symbol_master']}
    WHERE status = 'ACTIVE'
      AND market = :market
      AND ({category_expr('name')}) = :category
    ORDER BY name
    """
    rows = fetch_all(sql, {"market": market, "category": category})
    return [{"symbol": row["symbol"], "name": row.get("name")} for row in rows]
