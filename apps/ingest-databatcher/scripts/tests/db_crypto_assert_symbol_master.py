#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 검증 유틸: crypto_symbol_master 적재 여부 확인

사용자 실행(예):
  python scripts/tests/db_crypto_assert_symbol_master.py --quote USDT --limit 10

출력:
- quote/status별 row 수
- 샘플 심볼 목록

주의
- Copilot은 이 파일을 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text

# 프로젝트 루트 import 경로 주입
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--quote", default="USDT", help="quote_asset filter (default: USDT)")
    p.add_argument("--limit", type=int, default=10, help="sample rows to print")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    # 1) counts by quote/status
    sql_counts = text(
        """
        SELECT quote_asset, status, COUNT(*) AS cnt
        FROM crypto_symbol_master
        WHERE quote_asset = :quote
        GROUP BY quote_asset, status
        ORDER BY status
        """
    )

    # 2) sample
    sql_sample = text(
        """
        SELECT symbol, base_asset, quote_asset, status, exchange, etl_loaded_at
        FROM crypto_symbol_master
        WHERE quote_asset = :quote
        ORDER BY symbol
        LIMIT :limit
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql_counts, {"quote": args.quote}).fetchall()
        print("[crypto_symbol_master] counts")
        if not rows:
            print("  (no rows)")
        else:
            for r in rows:
                print(f"  quote={r.quote_asset} status={r.status} cnt={r.cnt}")

        print("\n[crypto_symbol_master] sample")
        sample = conn.execute(sql_sample, {"quote": args.quote, "limit": args.limit}).fetchall()
        if not sample:
            print("  (no rows)")
        else:
            for r in sample:
                print(
                    f"  {r.symbol} base={r.base_asset} quote={r.quote_asset} status={r.status} exchange={r.exchange} loaded_at={r.etl_loaded_at}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
