from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from .config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)


@contextmanager
def get_conn() -> Connection:
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def execute_write(sql: str, params: dict[str, Any] | None = None) -> int:
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount or 0


def verify_db_connection() -> None:
    try:
        with get_conn() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError("Database connection failed. Check DATABASE_URL and DB reachability.") from exc


def normalize_row(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: normalize_row(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_row(v) for v in value]
    return value
