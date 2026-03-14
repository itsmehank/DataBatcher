#!/usr/bin/env python3
"""
FDR Stock Probe
- Fetches data using FinanceDataReader for a given symbol and date range.
- Prints columns, head/tail samples, shape, date span, and basic NA stats.
Usage:
  python scripts/probes/fdr_stock_probe.py --symbol 005930 --start 2020-01-01 --end 2020-12-31
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime

import pandas as pd
import FinanceDataReader as fdr


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FDR stock data probe")
    p.add_argument("--symbol", required=True, help="Ticker symbol (e.g., 005930)")
    p.add_argument("--start", required=False, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=False, help="End date YYYY-MM-DD")
    return p.parse_args()


def main():
    args = parse_args()
    start = args.start or "2019-01-01"
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    print(f"[probe] Fetching {args.symbol} from {start} to {end} ...")
    try:
        df = fdr.DataReader(args.symbol, start=start, end=end)
    except Exception as e:
        print(f"[probe] Error during fetch: {e}", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        print("[probe] No data returned.")
        sys.exit(0)

    # Reset index to have date column explicit
    df = df.reset_index()

    print("\n[probe] Columns:")
    print(list(df.columns))

    print("\n[probe] Head:")
    print(df.head(5).to_string(index=False))

    print("\n[probe] Tail:")
    print(df.tail(5).to_string(index=False))

    print("\n[probe] Shape:")
    print(df.shape)

    # Date span
    try:
        dmin = pd.to_datetime(df.iloc[0, 0])
        dmax = pd.to_datetime(df.iloc[-1, 0])
        print(f"\n[probe] Date span: {dmin.date()} → {dmax.date()}")
    except Exception:
        pass

    # NA stats
    na_counts = df.isna().sum()
    total = len(df)
    print("\n[probe] NA counts (and ratio):")
    for col, cnt in na_counts.items():
        ratio = (cnt / total) if total else 0
        print(f"  - {col}: {cnt} ({ratio:.2%})")

    # Basic price stats if present
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            s = df[col].describe()
            print(f"\n[probe] {col} describe():\n{s}")

    print("\n[probe] Done.")


if __name__ == "__main__":
    main()
