#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance Spot(USDT) 코인 주봉(1w) bulk 적재 스크립트

범위
- 대상 심볼을 결정(우선순위: --all > --symbols > settings.yaml crypto.targets.symbols)
- Binance /api/v3/klines (interval=1w)로 주봉 OHLCV를 수집해 crypto_prices_weekly에 저장
- 옵션으로 indicators_crypto_weekly (SMA 20/50/100/200, EMA 21)을 계산해 crypto_indicators_weekly에 저장

저장 정책
- prices_weekly: insert_only (PK: symbol, week_start)
- indicators_weekly: insert_only (PK: symbol, week_start, indicator, params_hash)

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.crypto_binance import BinanceCryptoCollector
from core.config_loader import load_settings
from core.crypto_symbol_loader import load_crypto_symbols
from core.db_manager import DBConfig, DBManager
from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

# 지표 registry 등록(필수)
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Binance Spot USDT weekly bulk update")
    p.add_argument("--symbols", nargs="+", default=None, help="e.g., BTCUSDT ETHUSDT")
    p.add_argument("--all", action="store_true", help="process all ACTIVE symbols in crypto_symbol_master")
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (UTC date)")
    p.add_argument("--with-indicators", action="store_true")
    p.add_argument(
        "--skip-latest-week",
        action="store_true",
        help="safety: drop the latest returned weekly candle (in-progress week). Recommended for production bulk.",
    )
    return p.parse_args(argv)


def build_crypto_weekly_pipeline(cfg: dict) -> IndicatorPipeline:
    specs_cfg = (cfg.get("indicators_crypto_weekly", {}).get("pipeline") or [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def normalize_dates_to_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    s = pd.to_datetime(df[col], errors="coerce", utc=True)
    # numpy datetime64[ns] -> python datetime
    arr = s.to_numpy(dtype="datetime64[ns]")
    py = pd.to_datetime(arr, utc=True).to_pydatetime()
    df[col] = [x.date() if x is not None else None for x in py]
    return df


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


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

    start_d: date = _parse_date(args.start)
    end_d: date = _parse_date(args.end)

    print(f"[crypto_bulk_update_weekly] targets={len(symbols)} source={source_desc}")

    collector = BinanceCryptoCollector()

    pipeline = build_crypto_weekly_pipeline(cfg) if args.with_indicators else None
    saver = IndicatorSaver(engine, table_long="crypto_indicators_weekly") if args.with_indicators else None

    for sym in symbols:
        sym_u = sym.upper().strip()
        print(f"[crypto_bulk_update_weekly] symbol={sym_u} range={start_d}..{end_d}")

        df_weekly = collector.fetch_klines_1w(sym_u, start=start_d, end=end_d)
        if df_weekly is None or df_weekly.empty:
            print("  -> no weekly price data")
            continue

        # MySQL DATE
        df_weekly = normalize_dates_to_date(df_weekly, "week_start")
        df_weekly = normalize_dates_to_date(df_weekly, "week_end")

        if args.skip_latest_week and len(df_weekly) > 0:
            # 최신 week_start를 1개 드롭 (미완결 주 안전장치)
            df_weekly = df_weekly.sort_values("week_start")
            df_weekly = df_weekly.iloc[:-1].copy()
            print(f"  -> skip_latest_week: after_drop rows={len(df_weekly)}")

        price_rows = DBManager.upsert_dataframe(
            engine,
            df_weekly,
            table="crypto_prices_weekly",
            unique_keys=("symbol", "week_start"),
            mode="insert_only",
        )
        print(f"  -> weekly prices saved(insert_only) rows={price_rows}")

        if args.with_indicators and pipeline and saver:
            dfp = df_weekly.copy()
            dfp["week_start"] = pd.to_datetime(dfp["week_start"])
            dfp = dfp.sort_values("week_start")
            dfp.set_index("week_start", inplace=True)

            outputs = pipeline.run(dfp)
            if not outputs:
                print("  -> weekly indicators: no outputs")
                continue

            df_long = pipeline.to_long_dataframe(
                symbol=sym_u,
                market="BINANCE",  # 코인에서는 market 대신 exchange 역할
                source="binance",
                outputs=outputs,
                keep_nan=True,
            )

            if not df_long.empty:
                # date 컬럼명이 'date'로 나오므로 weekly 스키마에 맞춰 week_start로 rename
                if "date" in df_long.columns and "week_start" not in df_long.columns:
                    df_long = df_long.rename(columns={"date": "week_start"})

                s2 = pd.to_datetime(df_long["week_start"], errors="coerce", utc=True)
                arr2 = s2.to_numpy(dtype="datetime64[ns]")
                py2 = pd.to_datetime(arr2, utc=True).to_pydatetime()
                df_long["week_start"] = [x.date() if x is not None else None for x in py2]

                # crypto_indicators_weekly 컬럼명: exchange/source
                if "market" in df_long.columns and "exchange" not in df_long.columns:
                    df_long = df_long.rename(columns={"market": "exchange"})

                # keep_nan=True일 때 NaN/inf -> None
                df_long["value"] = df_long["value"].astype("object")
                df_long.loc[~np.isfinite(pd.to_numeric(df_long["value"], errors="coerce")), "value"] = None

            ind_rows = saver.save_long(df_long, mode="insert_only")
            print(f"  -> weekly indicators saved(insert_only) rows={ind_rows}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
