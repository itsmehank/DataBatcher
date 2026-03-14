#!/usr/bin/env python3
"""
FDR US Index Probe

FinanceDataReader에서 미국 지수(S&P 500, DJI, IXIC) 데이터가
어떤 포맷으로 반환되는지 검증합니다.

- 반환 컬럼명, 인덱스 형식, 데이터 타입 확인
- US500 (S&P 500), DJI (Dow Jones), IXIC (NASDAQ Composite)

Usage:
  python scripts/probes/fdr_us_index_probe.py --symbol US500 --start 2024-01-01 --end 2024-01-31
  python scripts/probes/fdr_us_index_probe.py --all-indices --start 2024-01-01 --end 2024-01-31
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime


# FDR 심볼 → 이름 매핑
US_INDICES = {
    'US500': 'S&P 500',
    'DJI':   'Dow Jones Industrial Average',
    'IXIC':  'NASDAQ Composite',
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FDR US Index data probe")
    p.add_argument("--symbol", default=None,
                   help="FDR index symbol (e.g., US500, DJI, IXIC)")
    p.add_argument("--all-indices", action="store_true",
                   help="Test all 3 US indices")
    p.add_argument("--start", required=False, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=False, help="End date YYYY-MM-DD")
    return p.parse_args()


def probe_index(symbol: str, start: str, end: str) -> None:
    """Probe a single US index via FDR."""
    import FinanceDataReader as fdr

    name = US_INDICES.get(symbol, symbol)
    print(f"\n{'=' * 60}")
    print(f"[probe] Fetching {symbol} ({name}) from {start} to {end} ...")
    print(f"{'=' * 60}")

    try:
        df = fdr.DataReader(symbol, start=start, end=end)
    except Exception as e:
        print(f"[probe] Error during fetch: {e}", file=sys.stderr)
        return

    if df is None or df.empty:
        print("[probe] No data returned.")
        return

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

    # Basic stats
    for col in df.columns:
        s = df[col].describe()
        print(f"\n[probe] {col} describe():\n{s}")

    print(f"\n[probe] {symbol} Done.")


def main():
    args = parse_args()
    start = args.start or "2024-01-01"
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    if args.all_indices:
        for symbol in US_INDICES:
            probe_index(symbol, start, end)
    elif args.symbol:
        probe_index(args.symbol, start, end)
    else:
        print("Error: --symbol 또는 --all-indices 중 하나를 지정하세요.", file=sys.stderr)
        sys.exit(2)

    print("\n[probe] All done.")


if __name__ == "__main__":
    main()
