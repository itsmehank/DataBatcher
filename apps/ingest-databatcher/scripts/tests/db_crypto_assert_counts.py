#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 검증 유틸: crypto_prices_daily / crypto_indicators_daily 적재 여부 확인

사용자 실행(예)
1) 기간 지정:
  python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31

2) 최근 N일:
  python scripts/tests/db_crypto_assert_counts.py --symbol BTCUSDT --days 35

출력(핵심)
- prices rows, min(date), max(date)
- indicators rows, distinct indicator 목록

주의
- Copilot은 이 파일을 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


@dataclass(frozen=True)
class Range:
    start: date
    end: date


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", type=int, help="최근 N일 범위로 조회 (UTC date 기준)")
    g.add_argument("--start", type=str, help="YYYY-MM-DD")

    p.add_argument("--end", type=str, help="YYYY-MM-DD (start 모드에서 필수)")

    return p.parse_args()


def resolve_range(args: argparse.Namespace) -> Range:
    if args.days is not None:
        # crypto_daily_update(최신) 기준과 동일: end=UTC 어제
        end = datetime.now(timezone.utc).date() - timedelta(days=1)
        start = end - timedelta(days=int(args.days))
        return Range(start=start, end=end)

    if not args.start or not args.end:
        raise SystemExit("--start 모드에서는 --end가 필수입니다.")
    return Range(start=_parse_date(args.start), end=_parse_date(args.end))


def main() -> int:
    args = parse_args()
    r = resolve_range(args)

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    sql_prices = text(
        """
        SELECT COUNT(*) AS cnt, MIN(date) AS min_date, MAX(date) AS max_date
        FROM crypto_prices_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    sql_ind = text(
        """
        SELECT COUNT(*) AS cnt, MIN(date) AS min_date, MAX(date) AS max_date
        FROM crypto_indicators_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    sql_indicators_distinct = text(
        """
        SELECT indicator, COUNT(*) AS cnt
        FROM crypto_indicators_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        GROUP BY indicator
        ORDER BY indicator
        """
    )

    params = {"symbol": args.symbol, "start": r.start, "end": r.end}

    print(f"[range] start={r.start} end={r.end} (inclusive)")
    print(f"[symbol] {args.symbol}")

    with engine.connect() as conn:
        pr = conn.execute(sql_prices, params).mappings().one()
        ir = conn.execute(sql_ind, params).mappings().one()
        inds = conn.execute(sql_indicators_distinct, params).fetchall()

    print("\n[crypto_prices_daily]")
    print(f"  rows={int(pr['cnt'])} min_date={pr['min_date']} max_date={pr['max_date']}")

    print("\n[crypto_indicators_daily]")
    print(f"  rows={int(ir['cnt'])} min_date={ir['min_date']} max_date={ir['max_date']}")

    print("\n[crypto_indicators_daily] distinct indicators")
    if not inds:
        print("  (no rows)")
    else:
        for ind, cnt in inds:
            print(f"  {ind}: {cnt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
