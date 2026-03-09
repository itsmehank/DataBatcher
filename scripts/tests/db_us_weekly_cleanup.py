#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cleanup helper for US stock weekly test data.

기능
- 지정한 symbol + week_start 기간에 대해
  - us_stock_indicators_weekly 삭제
  - us_stock_prices_weekly 삭제
- 기본은 실제 삭제 수행
- --dry-run 시 삭제 건수만 출력

사용 예
  python scripts/tests/db_us_weekly_cleanup.py --symbol AAPL --start 2024-01-01 --end 2024-03-31
  python scripts/tests/db_us_weekly_cleanup.py --symbol AAPL --start 2024-01-01 --end 2024-03-31 --dry-run
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings  # noqa: E402
from core.db_manager import DBConfig, DBManager  # noqa: E402


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", required=True, help="YYYY-MM-DD (week_start range, inclusive)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (week_start range, inclusive)")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    symbol = args.symbol.upper().strip()
    start_d = _parse_date(args.start)
    end_d = _parse_date(args.end)

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    print(f"[range] start={start_d} end={end_d} (week_start inclusive)")
    print(f"[symbol] {symbol}")

    q_cnt_i = text(
        """
        SELECT COUNT(*) AS cnt
        FROM us_stock_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )
    q_cnt_p = text(
        """
        SELECT COUNT(*) AS cnt
        FROM us_stock_prices_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    d_i = text(
        """
        DELETE FROM us_stock_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )
    d_p = text(
        """
        DELETE FROM us_stock_prices_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    # 1) counts
    with engine.connect() as conn:
        ci = conn.execute(q_cnt_i, {"symbol": symbol, "start": start_d, "end": end_d}).scalar_one()
        cp = conn.execute(q_cnt_p, {"symbol": symbol, "start": start_d, "end": end_d}).scalar_one()

    print(f"[target counts] indicators={ci} prices={cp}")

    if args.dry_run:
        print("[dry-run] no delete executed")
        return 0

    # 2) delete
    with engine.begin() as conn:
        ri = conn.execute(d_i, {"symbol": symbol, "start": start_d, "end": end_d}).rowcount
        rp = conn.execute(d_p, {"symbol": symbol, "start": start_d, "end": end_d}).rowcount

    print(f"[deleted] us_stock_indicators_weekly={ri} us_stock_prices_weekly={rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
