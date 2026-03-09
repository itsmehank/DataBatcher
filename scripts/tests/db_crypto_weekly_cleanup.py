#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cleanup helper for crypto weekly test data.

원칙
- Copilot은 직접 DB 삭제를 실행하지 않습니다.
- 사용자가 이 스크립트를 실행하고 출력 결과를 첨부하면, 오류/경계 조건을 점검합니다.

기능
- 지정한 symbol + week_start 기간에 대해
  - crypto_indicators_weekly 삭제
  - crypto_prices_weekly 삭제
- 기본은 실제 삭제 수행
- --dry-run 시 삭제 건수만 출력

사용 예
  python scripts/tests/db_crypto_weekly_cleanup.py --symbol BTCUSDT --start 2025-01-01 --end 2025-03-31
  python scripts/tests/db_crypto_weekly_cleanup.py --symbol BTCUSDT --start 2025-01-01 --end 2025-03-31 --dry-run
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
        FROM crypto_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )
    q_cnt_p = text(
        """
        SELECT COUNT(*) AS cnt
        FROM crypto_prices_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    d_i = text(
        """
        DELETE FROM crypto_indicators_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )
    d_p = text(
        """
        DELETE FROM crypto_prices_weekly
        WHERE symbol=:symbol
          AND week_start >= :start
          AND week_start <= :end
        """
    )

    # 1) counts: 별도 connection (SELECT 시 autobegin 발생 가능)
    with engine.connect() as conn:
        ci = conn.execute(q_cnt_i, {"symbol": symbol, "start": start_d, "end": end_d}).scalar_one()
        cp = conn.execute(q_cnt_p, {"symbol": symbol, "start": start_d, "end": end_d}).scalar_one()

    print(f"[target counts] indicators={ci} prices={cp}")

    if args.dry_run:
        print("[dry-run] no delete executed")
        return 0

    # 2) delete: 별도 transaction (engine.begin() 사용)
    with engine.begin() as conn:
        ri = conn.execute(d_i, {"symbol": symbol, "start": start_d, "end": end_d}).rowcount
        rp = conn.execute(d_p, {"symbol": symbol, "start": start_d, "end": end_d}).rowcount

    print(f"[deleted] crypto_indicators_weekly={ri} crypto_prices_weekly={rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
