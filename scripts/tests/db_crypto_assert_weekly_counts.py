#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB assert helper for crypto weekly tables.

원칙
- Copilot은 직접 DB 쿼리를 실행하지 않습니다.
- 사용자가 이 스크립트를 실행하고 출력 결과를 첨부하면, 그 결과로 다음 단계(수정/보완)를 진행합니다.

기능
- crypto_prices_weekly / crypto_indicators_weekly에 대해
  - 지정한 심볼 + 기간(week_start 기준) row 수
  - min/max week_start
  - indicator별 row 수(지표 테이블)

사용 예
  python scripts/tests/db_crypto_assert_weekly_counts.py --symbol BTCUSDT --start 2025-01-01 --end 2025-03-31
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

    q_prices = text(
        """
        SELECT COUNT(*) AS cnt,
               MIN(week_start) AS min_ws,
               MAX(week_start) AS max_ws
        FROM crypto_prices_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    q_inds = text(
        """
        SELECT COUNT(*) AS cnt,
               MIN(week_start) AS min_ws,
               MAX(week_start) AS max_ws
        FROM crypto_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    q_ind_dist = text(
        """
        SELECT indicator, COUNT(*) AS cnt
        FROM crypto_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        GROUP BY indicator
        ORDER BY indicator
        """
    )

    with engine.connect() as conn:
        r1 = conn.execute(q_prices, {"symbol": symbol, "start": start_d, "end": end_d}).mappings().first()
        r2 = conn.execute(q_inds, {"symbol": symbol, "start": start_d, "end": end_d}).mappings().first()
        rows = conn.execute(q_ind_dist, {"symbol": symbol, "start": start_d, "end": end_d}).mappings().all()

    print("\n[crypto_prices_weekly]")
    print(f"  rows={r1['cnt']} min_week_start={r1['min_ws']} max_week_start={r1['max_ws']}")

    print("\n[crypto_indicators_weekly]")
    print(f"  rows={r2['cnt']} min_week_start={r2['min_ws']} max_week_start={r2['max_ws']}")

    print("\n[crypto_indicators_weekly] distinct indicators")
    if not rows:
        print("  (no rows)")
    else:
        for rr in rows:
            print(f"  {rr['indicator']}: {rr['cnt']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
