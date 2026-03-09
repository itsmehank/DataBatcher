#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance(Spot) 코인 심볼 마스터 동기화 스크립트

목표
- Binance exchangeInfo에서 Spot + TRADING + quoteAsset=USDT 인 페어를 가져와
  `crypto_symbol_master` 테이블에 저장합니다.

저장 정책
- insert-only가 아니라 "upsert"(동일 symbol이면 status/base/quote/exchange 최신화)
  * 심볼 마스터는 원천 상태를 따라가는 것이 일반적으로 맞습니다.

실행 예
- 전체 USDT 페어:
    python scripts/crypto_sync_symbol_master.py --all
- 일부 심볼만(테스트용):
    python scripts/crypto_sync_symbol_master.py --symbols BTCUSDT ETHUSDT

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 로그를 첨부해주세요.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector
from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="sync all spot+TRADING USDT pairs")
    g.add_argument("--symbols", nargs="+", help="sync only given symbols (e.g., BTCUSDT ETHUSDT)")
    return p.parse_args()


def upsert_crypto_symbol_master(engine, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0

    sql = text(
        """
        INSERT INTO crypto_symbol_master
          (symbol, base_asset, quote_asset, status, exchange, etl_loaded_at)
        VALUES
          (:symbol, :base_asset, :quote_asset, :status, :exchange, NOW())
        ON DUPLICATE KEY UPDATE
          base_asset=VALUES(base_asset),
          quote_asset=VALUES(quote_asset),
          status=VALUES(status),
          exchange=VALUES(exchange),
          etl_loaded_at=VALUES(etl_loaded_at)
        """
    )

    rows = df.to_dict(orient="records")
    with engine.begin() as conn:
        for r in rows:
            conn.execute(sql, r)
    return len(rows)


def main() -> int:
    args = parse_args()

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    collector = BinanceCryptoCollector()
    all_pairs = collector.list_spot_usdt_symbols()

    if args.symbols:
        wanted = {s.upper().strip() for s in args.symbols}
        rows = [r for r in all_pairs if r["symbol"] in wanted]
    else:
        rows = all_pairs

    df = pd.DataFrame(rows)

    print(f"[crypto_sync_symbol_master] fetched={len(all_pairs)} (spot+TRADING+USDT)")
    if args.symbols:
        print(f"[crypto_sync_symbol_master] filtered={len(df)} symbols={sorted(set(df['symbol'].tolist())) if not df.empty else []}")

    saved = upsert_crypto_symbol_master(engine, df)
    print(f"[crypto_sync_symbol_master] saved_rows={saved}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
