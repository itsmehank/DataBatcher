#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binance Spot(USDT) 코인 주봉(1w) weekly update

목적
- 주기적으로 실행하며, 최근 완결된 주봉 데이터를 DB에 insert-only로 적재한다.
- 옵션으로 주봉 지표(indicators_crypto_weekly)를 계산해 insert-only로 적재한다.

정책(코인/UTC 기준)
- 코인은 24/7 이므로, '완결된 주'만 적재하기 위해 기본 end date를 UTC 기준 '어제'로 둔다.
- 그리고 안전장치로, 수집된 weekly_df에서 가장 최신 week_start 1개를 drop 한다.
  (bulk_update_weekly에서 사용하던 safety 스킵과 동일)

대상 심볼 결정 우선순위
1) --all 지정: crypto_symbol_master ACTIVE 전체
2) --symbols 지정: 해당 심볼만
3) 둘 다 없으면: config/settings.yaml 의 crypto.targets.symbols

저장 정책
- 가격: crypto_prices_weekly insert_only
- 지표: crypto_indicators_weekly insert_only

사용 예
  python scripts/crypto_weekly_update.py --symbols BTCUSDT --with-indicators
  python scripts/crypto_weekly_update.py --all --with-indicators

주의
- Copilot은 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
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

# 주봉 지표 warmup 고려(가장 긴 SMA 200 + 여유)
LOOKBACK_WEEKS = 260


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Binance Spot USDT weekly update")
    p.add_argument("--all", action="store_true")
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument(
        "--end",
        default=None,
        help="YYYY-MM-DD (UTC date). default: (UTC yesterday) to ensure completed candles",
    )
    p.add_argument("--with-indicators", action="store_true")
    p.add_argument(
        "--skip-latest-week",
        dest="skip_latest_week",
        action="store_true",
        help="Drop the latest returned weekly candle as safety.",
    )
    p.add_argument(
        "--no-skip-latest-week",
        dest="skip_latest_week",
        action="store_false",
        help="Do NOT drop the latest weekly candle.",
    )
    p.set_defaults(skip_latest_week=True)
    return p.parse_args(argv)


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def default_end_date_utc_yesterday() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def normalize_dates_to_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    s = pd.to_datetime(df[col], errors="coerce", utc=True)
    arr = s.to_numpy(dtype="datetime64[ns]")
    py = pd.to_datetime(arr, utc=True).to_pydatetime()
    df[col] = [x.date() if x is not None else None for x in py]
    return df


def build_crypto_weekly_pipeline(cfg: dict) -> IndicatorPipeline:
    specs_cfg = (cfg.get("indicators_crypto_weekly", {}).get("pipeline") or [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


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
            "Error: 처리할 crypto 심볼이 없습니다. --all 또는 --symbols를 지정하거나, config/settings.yaml의 crypto.targets.symbols를 채워주세요.",
            file=sys.stderr,
        )
        return 2

    end_d: date = _parse_date(args.end) if args.end else default_end_date_utc_yesterday()
    start_d: date = end_d - timedelta(weeks=LOOKBACK_WEEKS)

    print(f"[crypto_weekly_update] targets={len(symbols)} source={source_desc}")
    print(f"[crypto_weekly_update] range={start_d}..{end_d} weeks={LOOKBACK_WEEKS} (fixed)")

    collector = BinanceCryptoCollector()

    pipeline = build_crypto_weekly_pipeline(cfg) if args.with_indicators else None
    saver = IndicatorSaver(engine, table_long="crypto_indicators_weekly") if args.with_indicators else None

    for sym in symbols:
        sym_u = sym.upper().strip()
        print(f"[crypto_weekly_update] symbol={sym_u}")

        df_weekly = collector.fetch_klines_1w(sym_u, start=start_d, end=end_d)
        if df_weekly is None or df_weekly.empty:
            print("  -> no weekly price data")
            continue

        df_weekly = normalize_dates_to_date(df_weekly, "week_start")
        df_weekly = normalize_dates_to_date(df_weekly, "week_end")

        if args.skip_latest_week and len(df_weekly) > 0:
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
            df_long = pipeline.to_long_dataframe(
                symbol=sym_u,
                market="BINANCE",
                source="binance",
                outputs=outputs,
                keep_nan=True,
            )

            if not df_long.empty:
                if "date" in df_long.columns and "week_start" not in df_long.columns:
                    df_long = df_long.rename(columns={"date": "week_start"})

                s2 = pd.to_datetime(df_long["week_start"], errors="coerce", utc=True)
                arr2 = s2.to_numpy(dtype="datetime64[ns]")
                py2 = pd.to_datetime(arr2, utc=True).to_pydatetime()
                df_long["week_start"] = [x.date() if x is not None else None for x in py2]

                if "market" in df_long.columns and "exchange" not in df_long.columns:
                    df_long = df_long.rename(columns={"market": "exchange"})

                df_long["value"] = df_long["value"].astype("object")
                df_long.loc[~np.isfinite(pd.to_numeric(df_long["value"], errors="coerce")), "value"] = None

            ind_rows = saver.save_long(df_long, mode="insert_only")
            print(f"  -> weekly indicators saved(insert_only) rows={ind_rows}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
