from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException


def parse_date(value: str | None, default: date) -> str:
    if not value:
        return default.isoformat()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc


def category_expr(name_col: str = "name") -> str:
    return (
        "CASE "
        f"WHEN LEFT(TRIM({name_col}), 1) BETWEEN '0' AND '9' THEN '0-9' "
        f"ELSE UPPER(LEFT(TRIM({name_col}), 1)) END"
    )


def parse_region_key(region: str) -> str:
    key = region.upper()
    if key not in {"US", "KR"}:
        raise HTTPException(status_code=400, detail="Invalid region")
    return key
