#!/usr/bin/env python3
"""
yfinance US Stock Probe

- yfinance 일봉 응답 포맷과 컬럼 구조 확인
- MultiIndex 컬럼 flatten 가능 여부 확인
- 현재 us_stock_prices 적재 스키마로 정규화 가능한지 미리보기 제공

Usage:
  python scripts/probes/yfinance_us_stock_probe.py
  python scripts/probes/yfinance_us_stock_probe.py --symbol BRK-B --start 2025-12-01 --end 2025-12-10
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="yfinance US stock data probe")
    p.add_argument("--symbol", default="AAPL", help="Ticker symbol (default: AAPL)")
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
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    df["symbol"] = symbol
    df["market"] = "PROBE"
    df["source"] = "yfinance"
    df["date"] = pd.to_datetime(df["date"]).dt.date

    expected = [
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "market",
        "source",
    ]
    available = [col for col in expected if col in df.columns]
    return df[available]


def main() -> int:
    args = parse_args()
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    print("=" * 60)
    print("yfinance US Stock Probe")
    print("=" * 60)
    print(f"[probe] download(symbol={args.symbol}, start={args.start}, end={end}, auto_adjust=False)")

    try:
        df = yf.download(args.symbol, start=args.start, end=end, auto_adjust=False, progress=False)
    except Exception as exc:
        print(f"[probe] Error: {exc}", file=sys.stderr)
        return 1

    if df is None or df.empty:
        print("[probe] No data returned.")
        return 0

    print(f"[probe] Raw shape: {df.shape}")
    print(f"[probe] Raw columns: {list(df.columns)}")

    flat = flatten_columns(df)
    print(f"[probe] Flattened columns: {list(flat.columns)}")
    print("[probe] Raw head (3 rows):")
    print(df.head(3).to_string())

    preview = normalize_preview(df, args.symbol)
    print("[probe] Normalized preview head (3 rows):")
    print(preview.head(3).to_string(index=False))

    dmin = preview["date"].min()
    dmax = preview["date"].max()
    print(f"[probe] Date span: {dmin} -> {dmax}")
    print(f"[probe] Normalized columns: {list(preview.columns)}")
    print("[probe] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
