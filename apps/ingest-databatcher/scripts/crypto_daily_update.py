#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance Spot(USDT) 코인 일봉 daily update

정책(현재 코인 범위)
- 대상 심볼 결정 우선순위:
  1) --all 지정 시: crypto_symbol_master의 ACTIVE 전체
  2) --symbols 지정 시: 해당 심볼만
  3) 둘 다 없으면: apps/ingest-databatcher/config/settings.yaml의 crypto.targets.symbols

- 최근 50일만 업데이트(고정)
- 기본 end date: 실행 시점 UTC 날짜 기준 "어제" (완결된 일봉만 적재)
- 가격: insert_only
- 지표: insert_only
- 지표는 keep_nan=True로 row를 만들고, NaN은 DB NULL로 저장

실행 예
  python scripts/crypto_daily_update.py --symbols BTCUSDT --with-indicators
  python scripts/crypto_daily_update.py --all --with-indicators

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector
from core.config_loader import load_settings
from core.crypto_symbol_loader import load_crypto_symbols
from core.db_manager import DBConfig, DBManager
from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

# 지표 registry 등록
from indicators.common import sma as _reg_sma  # noqa: F401

# 고정 업데이트 범위(UTC date 기준)
LOOKBACK_DAYS = 50


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Binance Spot USDT daily update")
    p.add_argument("--all", action="store_true")
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument(
        "--end",
        default=None,
        help="YYYY-MM-DD (UTC date). default: (UTC yesterday) to ensure completed daily candle",
    )
    p.add_argument("--with-indicators", action="store_true")
    return p.parse_args(argv)


def build_crypto_pipeline(cfg: dict) -> IndicatorPipeline:
    specs_cfg = (cfg.get("indicators_crypto_daily", {}).get("pipeline") or [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def default_end_date_utc_yesterday() -> date:
    """완결된 일봉만 적재하기 위해 UTC 기준 '어제'를 기본 end date로 사용."""
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def main(argv=None) -> int:
    args = parse_args(argv)

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    # 대상 심볼 결정
    if args.all:
        symbols = load_crypto_symbols(engine, all_active=True)
        source_desc = "--all (crypto_symbol_master ACTIVE)"
    elif args.symbols:
        symbols = load_crypto_symbols(engine, symbols=args.symbols)
        source_desc = "--symbols"
    else:
        default_symbols = ((cfg.get("crypto") or {}).get("targets") or {}).get("symbols") or []
        symbols = [str(s).upper().strip() for s in default_symbols if s and str(s).strip()]
        source_desc = "config: crypto.targets.symbols"

    if not symbols:
        print(
            "Error: 처리할 crypto 심볼이 없습니다. --all 또는 --symbols를 지정하거나, apps/ingest-databatcher/config/settings.yaml의 crypto.targets.symbols를 채워주세요.",
            file=sys.stderr,
        )
        return 2

    end_d: date = pd.to_datetime(args.end).date() if args.end else default_end_date_utc_yesterday()
    start_d: date = end_d - timedelta(days=LOOKBACK_DAYS)

    print(f"[crypto_daily_update] targets={len(symbols)} source={source_desc}")
    print(f"[crypto_daily_update] range={start_d}..{end_d} days={LOOKBACK_DAYS} (fixed)")

    collector = BinanceCryptoCollector()

    pipeline = build_crypto_pipeline(cfg) if args.with_indicators else None
    saver = IndicatorSaver(engine, table_long="crypto_indicators_daily") if args.with_indicators else None

    for sym in symbols:
        sym_u = sym.upper().strip()
        print(f"[crypto_daily_update] symbol={sym_u}")

        df_price = collector.fetch_klines_1d(sym_u, start=start_d, end=end_d)
        if df_price is None or df_price.empty:
            print("  -> no price data")
            continue

        # date 타입
        df_price["date"] = pd.to_datetime(df_price["date"]).dt.date

        price_rows = DBManager.upsert_dataframe(engine, df_price, table="crypto_prices_daily", mode="insert_only")
        print(f"  -> prices saved(insert_only) rows={price_rows}")

        if args.with_indicators and pipeline and saver:
            dfp = df_price.copy()
            dfp["date"] = pd.to_datetime(dfp["date"])
            dfp.set_index("date", inplace=True)

            outputs = pipeline.run(dfp)
            df_long = pipeline.to_long_dataframe(
                symbol=sym_u,
                market="BINANCE",
                source="binance",
                outputs=outputs,
                keep_nan=True,
            )

            # crypto_indicators_daily 컬럼명: exchange/source
            if not df_long.empty:
                df_long["date"] = pd.to_datetime(df_long["date"]).dt.date
                if "market" in df_long.columns and "exchange" not in df_long.columns:
                    df_long = df_long.rename(columns={"market": "exchange"})

            ind_rows = saver.save_long(df_long, mode="insert_only")
            print(f"  -> indicators saved(insert_only) rows={ind_rows}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
