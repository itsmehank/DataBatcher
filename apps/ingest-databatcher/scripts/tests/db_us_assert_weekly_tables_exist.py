#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assert US stock weekly tables/views exist.

기능
- DATABASE() 기준으로 아래 객체 존재 여부를 확인:
  - us_stock_prices_weekly
  - us_stock_indicators_weekly
  - v_us_stock_price_weekly_with_ma

사용 예
  python scripts/tests/db_us_assert_weekly_tables_exist.py
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings  # noqa: E402
from core.db_manager import DBConfig, DBManager  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _exists(conn, name: str) -> bool:
    sql = """
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = :name
    LIMIT 1
    """
    r = conn.execute(text(sql), {"name": name}).fetchone()
    if r:
        return True

    # views도 tables에 들어가지만, 혹시를 대비해 views도 확인
    sql2 = """
    SELECT 1
    FROM information_schema.views
    WHERE table_schema = DATABASE()
      AND table_name = :name
    LIMIT 1
    """
    r2 = conn.execute(text(sql2), {"name": name}).fetchone()
    return bool(r2)


def main() -> int:
    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    targets = [
        "us_stock_prices_weekly",
        "us_stock_indicators_weekly",
        "v_us_stock_price_weekly_with_ma",
    ]

    print("[db] US Weekly tables/views existence")
    all_ok = True
    with engine.connect() as conn:
        for t in targets:
            ok = _exists(conn, t)
            print(f"  {t}: {'OK' if ok else 'MISSING'}")
            if not ok:
                all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
