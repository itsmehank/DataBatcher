#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance Spot(USDT) 코인 일봉 bulk 적재 스크립트

범위
- crypto_symbol_master에서 대상 심볼을 읽고
- Binance /api/v3/klines (interval=1d)로 OHLCV를 수집해 crypto_prices_daily에 저장
- 옵션으로 indicators_crypto_daily (SMA 5/20/40)를 계산해 crypto_indicators_daily에 저장

저장 정책
- prices: insert_only (PK: symbol,date)
- indicators: insert_only (PK: symbol,date,indicator,params_hash)

실행 예
- 단일 심볼 1개월 + 지표
  python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT --start 2026-01-01 --end 2026-01-31 --with-indicators

- 여러 심볼
  python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT ETHUSDT --start 2026-01-01 --end 2026-01-31 --with-indicators

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector
from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.crypto_symbol_loader import load_crypto_symbols
from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

# 지표 registry 등록
from indicators.common import sma as _reg_sma  # noqa: F401


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Binance Spot USDT daily bulk update")
    p.add_argument("--symbols", nargs="+", default=None, help="e.g., BTCUSDT ETHUSDT")
    p.add_argument("--all", action="store_true", help="process all ACTIVE symbols in crypto_symbol_master")
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--with-indicators", action="store_true")
    return p.parse_args(argv)


def build_crypto_pipeline(cfg: dict) -> IndicatorPipeline:
    specs_cfg = (cfg.get("indicators_crypto_daily", {}).get("pipeline") or [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def normalize_dates_to_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df[col] = pd.to_datetime(df[col]).dt.date
    return df


def main(argv=None) -> int:
    args = parse_args(argv)

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    # 대상 심볼 결정 (우선순위: --all > --symbols > settings.yaml)
    if args.all:
        symbols = load_crypto_symbols(engine, all_active=True)
        source_desc = "--all (crypto_symbol_master ACTIVE)"
    elif args.symbols:
        symbols = load_crypto_symbols(engine, symbols=args.symbols)
        source_desc = "--symbols"
    else:
        default_symbols = (
            (cfg.get("crypto") or {}).get("targets") or {}
        ).get("symbols") or []
        symbols = [str(s).upper().strip() for s in default_symbols if s and str(s).strip()]
        source_desc = "config: crypto.targets.symbols"

    if not symbols:
        print(
            "Error: 처리할 crypto 심볼이 없습니다. --all 또는 --symbols를 지정하거나, config/settings.yaml의 crypto.targets.symbols를 채워주세요.",
            file=sys.stderr,
        )
        return 2

    print(f"[crypto_bulk_update_daily] targets={len(symbols)} source={source_desc}")

    collector = BinanceCryptoCollector()

    start_d: date = pd.to_datetime(args.start).date()
    end_d: date = pd.to_datetime(args.end).date()

    pipeline = build_crypto_pipeline(cfg) if args.with_indicators else None
    saver = IndicatorSaver(engine, table_long="crypto_indicators_daily") if args.with_indicators else None

    for sym in symbols:
        sym_u = sym.upper().strip()
        print(f"[crypto_bulk_update_daily] symbol={sym_u} range={start_d}..{end_d}")

        df_price = collector.fetch_klines_1d(sym_u, start=start_d, end=end_d)
        if df_price is None or df_price.empty:
            print(f"  -> no price data")
            continue

        # mysql DATE 컬럼 호환
        df_price = normalize_dates_to_date(df_price, "date")

        # prices insert_only
        price_rows = DBManager.upsert_dataframe(engine, df_price, table="crypto_prices_daily", mode="insert_only")
        print(f"  -> prices saved(insert_only) rows={price_rows}")

        if args.with_indicators and pipeline and saver:
            dfp = df_price.copy()
            dfp["date"] = pd.to_datetime(dfp["date"])
            dfp.set_index("date", inplace=True)

            outputs = pipeline.run(dfp)
            if not outputs:
                print("  -> indicators: no outputs")
                continue

            df_long = pipeline.to_long_dataframe(
                symbol=sym_u,
                market="BINANCE",  # 코인에서는 market 대신 exchange 역할
                source="binance",
                outputs=outputs,
                keep_nan=True,
            )
            if not df_long.empty:
                df_long["date"] = pd.to_datetime(df_long["date"]).dt.date

                # crypto_indicators_daily 컬럼명은 exchange/source 이므로 rename 필요
                if "market" in df_long.columns and "exchange" not in df_long.columns:
                    df_long = df_long.rename(columns={"market": "exchange"})

                # keep_nan=True인 경우 NaN/inf는 MySQL에 그대로 들어가면 오류.
                # 1) dtype을 object로 바꾸고
                # 2) NaN/inf 전부 None으로 치환
                df_long["value"] = df_long["value"].astype("object")
                df_long.loc[~np.isfinite(pd.to_numeric(df_long["value"], errors="coerce")), "value"] = None

            ind_rows = saver.save_long(df_long, mode="insert_only")
            print(f"  -> indicators saved(insert_only) rows={ind_rows}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
