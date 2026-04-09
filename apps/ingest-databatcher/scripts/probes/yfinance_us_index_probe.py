#!/usr/bin/env python3
"""
yfinance US Index Probe

- yfinance 지수 일봉 응답 포맷 확인
- 내부 심볼(US500/DJI/IXIC) -> Yahoo ticker 매핑 확인
- 현재 us_index_prices 적재 스키마로 정규화 가능한지 미리보기 제공

Usage:
  python scripts/probes/yfinance_us_index_probe.py --symbol US500 --start 2025-12-01 --end 2025-12-10
  python scripts/probes/yfinance_us_index_probe.py --all-indices
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


YF_INDEX_SYMBOL_MAP = {
    "US500": "^GSPC",
    "DJI": "^DJI",
    "IXIC": "^IXIC",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="yfinance US index data probe")
    p.add_argument("--symbol", default=None, help="Internal index symbol (US500, DJI, IXIC)")
    p.add_argument("--all-indices", action="store_true", help="Test all supported indices")
    p.add_argument("--start", default="2025-12-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default: today)")
    return p.parse_args()


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [str(col[0]) for col in df.columns]
    return df


def normalize_preview(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = flatten_columns(df)
    df = df.reset_index()

    date_col = df.columns[0]
    if date_col != "date":
        df = df.rename(columns={date_col: "date"})

    column_mapping = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    keep_cols = ["date", "open", "high", "low", "close", "volume"]
    df = df[[col for col in keep_cols if col in df.columns]]

    df["symbol"] = symbol
    df["market"] = symbol
    df["source"] = "yfinance"
    df["date"] = pd.to_datetime(df["date"]).dt.date

    expected = ["symbol", "date", "open", "high", "low", "close", "volume", "market", "source"]
    return df[expected]


def probe_index(symbol: str, start: str, end: str) -> None:
    yf_symbol = YF_INDEX_SYMBOL_MAP[symbol]
    print("=" * 60)
    print(f"[probe] {symbol} -> {yf_symbol}")
    print(f"[probe] download(start={start}, end={end}, auto_adjust=False)")
    print("=" * 60)

    df = yf.download(yf_symbol, start=start, end=end, auto_adjust=False, progress=False)
    if df is None or df.empty:
        print("[probe] No data returned.")
        return

    print(f"[probe] Raw shape: {df.shape}")
    print(f"[probe] Raw columns: {list(df.columns)}")

    flat = flatten_columns(df)
    print(f"[probe] Flattened columns: {list(flat.columns)}")
    print("[probe] Raw head (3 rows):")
    print(df.head(3).to_string())

    preview = normalize_preview(df, symbol)
    print("[probe] Normalized preview head (3 rows):")
    print(preview.head(3).to_string(index=False))

    dmin = preview["date"].min()
    dmax = preview["date"].max()
    print(f"[probe] Date span: {dmin} -> {dmax}")
    print(f"[probe] Normalized columns: {list(preview.columns)}")


def main() -> int:
    args = parse_args()
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    if args.all_indices:
        symbols = list(YF_INDEX_SYMBOL_MAP.keys())
    elif args.symbol:
        if args.symbol not in YF_INDEX_SYMBOL_MAP:
            print(f"Error: unsupported symbol '{args.symbol}'", file=sys.stderr)
            return 2
        symbols = [args.symbol]
    else:
        print("Error: --symbol 또는 --all-indices 중 하나를 지정하세요.", file=sys.stderr)
        return 2

    for symbol in symbols:
        try:
            probe_index(symbol, args.start, end)
        except Exception as exc:
            print(f"[probe] {symbol}: Error - {exc}", file=sys.stderr)
            return 1

    print("[probe] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
