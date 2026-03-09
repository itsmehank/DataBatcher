#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 정리 유틸: crypto_prices_daily / crypto_indicators_daily 테스트 데이터 삭제

사용자 실행(예)
1) 기간 지정:
  python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --start 2026-01-01 --end 2026-01-31

2) 최근 N일:
  python scripts/tests/db_crypto_cleanup.py --symbol BTCUSDT --days 35

삭제 순서(외래키는 없지만 안전하게)
1) crypto_indicators_daily
2) crypto_prices_daily

주의
- Copilot은 이 파일을 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
- 운영 데이터 삭제 위험이 있으니 반드시 symbol+기간 조건을 확인 후 사용하세요.
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
    g.add_argument("--days", type=int, help="최근 N일 범위로 삭제 (UTC date 기준)")
    g.add_argument("--start", type=str, help="YYYY-MM-DD")

    p.add_argument("--end", type=str, help="YYYY-MM-DD (start 모드에서 필수)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="삭제하지 않고 대상 row 수만 출력",
    )

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

    params = {"symbol": args.symbol, "start": r.start, "end": r.end}

    sql_count_ind = text(
        """
        SELECT COUNT(*) AS cnt
        FROM crypto_indicators_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    sql_count_prices = text(
        """
        SELECT COUNT(*) AS cnt
        FROM crypto_prices_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    sql_del_ind = text(
        """
        DELETE FROM crypto_indicators_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    sql_del_prices = text(
        """
        DELETE FROM crypto_prices_daily
        WHERE symbol = :symbol AND date >= :start AND date <= :end
        """
    )

    with engine.connect() as conn:
        ind_cnt = int(conn.execute(sql_count_ind, params).scalar_one())
        price_cnt = int(conn.execute(sql_count_prices, params).scalar_one())

    print(f"[range] start={r.start} end={r.end} (inclusive)")
    print(f"[symbol] {args.symbol}")
    print(f"[target counts] indicators={ind_cnt} prices={price_cnt}")

    if args.dry_run:
        print("[dry-run] no delete executed")
        return 0

    with engine.begin() as conn:
        del_ind = conn.execute(sql_del_ind, params).rowcount
        del_prices = conn.execute(sql_del_prices, params).rowcount

    print(f"[deleted] crypto_indicators_daily={del_ind} crypto_prices_daily={del_prices}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
