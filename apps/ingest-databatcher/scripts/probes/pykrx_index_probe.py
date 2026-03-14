#!/usr/bin/env python3
"""
pykrx 지수(Index) API Probe

pykrx의 get_index_ohlcv() 함수 동작을 확인합니다.
- 반환 컬럼명, 인덱스 형식, 데이터 타입 확인
- KOSPI(1001), KOSDAQ(2001) 지수 데이터 조회

Usage:
  python scripts/probes/pykrx_index_probe.py --index 1001 --start 2024-01-01 --end 2024-01-31
  python scripts/probes/pykrx_index_probe.py --index 2001 --start 2024-01-01 --end 2024-01-31
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime

import pandas as pd
from pykrx import stock


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="pykrx index OHLCV data probe")
    p.add_argument("--index", required=True, help="Index code (e.g., 1001 for KOSPI, 2001 for KOSDAQ)")
    p.add_argument("--start", required=False, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=False, help="End date YYYY-MM-DD")
    return p.parse_args()


def main():
    args = parse_args()
    start = args.start or "2024-01-01"
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    # pykrx 날짜 형식 변환 (YYYY-MM-DD → YYYYMMDD)
    start_str = start.replace("-", "")
    end_str = end.replace("-", "")

    print(f"[probe] Fetching index {args.index} from {start} to {end} ...")

    # 1. get_index_ohlcv 호출
    try:
        df = stock.get_index_ohlcv(start_str, end_str, args.index)
    except Exception as e:
        print(f"[probe] Error during fetch: {e}", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        print("[probe] No data returned.")
        sys.exit(0)

    print(f"\n[probe] Raw DataFrame info:")
    print(f"  Type: {type(df)}")
    print(f"  Shape: {df.shape}")
    print(f"  Index type: {type(df.index)}")
    print(f"  Index name: {df.index.name}")
    print(f"  Index dtype: {df.index.dtype}")

    print(f"\n[probe] Columns: {list(df.columns)}")
    print(f"[probe] Column dtypes:")
    for col in df.columns:
        print(f"  - {col}: {df[col].dtype}")

    print(f"\n[probe] Head (5 rows):")
    print(df.head(5).to_string())

    print(f"\n[probe] Tail (5 rows):")
    print(df.tail(5).to_string())

    # Date span
    try:
        dmin = df.index[0]
        dmax = df.index[-1]
        print(f"\n[probe] Date span: {dmin} → {dmax}")
    except Exception:
        pass

    # NA stats
    na_counts = df.isna().sum()
    total = len(df)
    print(f"\n[probe] NA counts (and ratio):")
    for col, cnt in na_counts.items():
        ratio = (cnt / total) if total else 0
        print(f"  - {col}: {cnt} ({ratio:.2%})")

    # Basic stats for price-like columns
    for col in df.columns:
        s = df[col].describe()
        print(f"\n[probe] {col} describe():\n{s}")

    # 2. get_index_ticker_name 테스트
    print(f"\n[probe] Testing get_index_ticker_name('{args.index}')...")
    try:
        name = stock.get_index_ticker_name(args.index)
        print(f"  Name: {name}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n[probe] Done.")


if __name__ == "__main__":
    main()
