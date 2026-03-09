#!/usr/bin/env python3
"""
FDR US Stock Probe
- FDR의 미국 주식 API 응답 포맷, 컬럼명, 데이터 타입 확인
- StockListing (NYSE, NASDAQ, ETF/US) 테스트
- DataReader (AAPL) 테스트

Usage:
  python scripts/probes/fdr_us_stock_probe.py
  python scripts/probes/fdr_us_stock_probe.py --symbol AAPL --start 2024-01-01 --end 2024-01-31
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime

import pandas as pd

try:
    import FinanceDataReader as fdr
except ImportError:
    print("Error: FinanceDataReader not installed. Run: pip install finance-datareader", file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FDR US stock data probe")
    p.add_argument("--symbol", default="AAPL", help="Ticker symbol (default: AAPL)")
    p.add_argument("--start", default="2024-01-01", help="Start date YYYY-MM-DD")
    p.add_argument("--end", default=None, help="End date YYYY-MM-DD (default: today)")
    p.add_argument("--skip-listing", action="store_true", help="Skip StockListing tests")
    return p.parse_args()


def test_stock_listing(market: str) -> pd.DataFrame | None:
    """StockListing API 테스트"""
    print(f"\n{'='*60}")
    print(f"[probe] Testing fdr.StockListing('{market}')...")
    print('='*60)

    try:
        df = fdr.StockListing(market)

        if df is None or df.empty:
            print(f"[probe] {market}: No data returned.")
            return None

        print(f"\n[probe] {market} - Shape: {df.shape}")
        print(f"\n[probe] {market} - Columns:")
        print(list(df.columns))
        print(f"\n[probe] {market} - Dtypes:")
        print(df.dtypes)
        print(f"\n[probe] {market} - Head (5 rows):")
        print(df.head(5).to_string(index=False))

        # sector/industry 컬럼 존재 여부 확인
        sector_cols = [col for col in df.columns if 'sector' in col.lower() or 'industry' in col.lower()]
        if sector_cols:
            print(f"\n[probe] {market} - Sector/Industry columns found: {sector_cols}")
        else:
            print(f"\n[probe] {market} - No sector/industry columns found")

        return df

    except Exception as e:
        print(f"[probe] {market}: Error - {e}", file=sys.stderr)
        return None


def test_data_reader(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    """DataReader API 테스트"""
    print(f"\n{'='*60}")
    print(f"[probe] Testing fdr.DataReader('{symbol}', '{start}', '{end}')...")
    print('='*60)

    try:
        df = fdr.DataReader(symbol, start=start, end=end)

        if df is None or df.empty:
            print(f"[probe] {symbol}: No data returned.")
            return None

        # Reset index to have date column explicit
        df = df.reset_index()

        print(f"\n[probe] {symbol} - Shape: {df.shape}")
        print(f"\n[probe] {symbol} - Columns:")
        print(list(df.columns))
        print(f"\n[probe] {symbol} - Dtypes:")
        print(df.dtypes)
        print(f"\n[probe] {symbol} - Head (5 rows):")
        print(df.head(5).to_string(index=False))
        print(f"\n[probe] {symbol} - Tail (5 rows):")
        print(df.tail(5).to_string(index=False))

        # Date span
        try:
            dmin = pd.to_datetime(df.iloc[0, 0])
            dmax = pd.to_datetime(df.iloc[-1, 0])
            print(f"\n[probe] {symbol} - Date span: {dmin.date()} → {dmax.date()}")
        except Exception:
            pass

        # NA stats
        na_counts = df.isna().sum()
        total = len(df)
        print(f"\n[probe] {symbol} - NA counts (and ratio):")
        for col, cnt in na_counts.items():
            ratio = (cnt / total) if total else 0
            print(f"  - {col}: {cnt} ({ratio:.2%})")

        # 컬럼 매핑 가이드 출력
        print(f"\n[probe] {symbol} - Column mapping guide:")
        expected_mapping = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume',
        }
        for fdr_col, db_col in expected_mapping.items():
            found = fdr_col in df.columns
            status = "✓" if found else "✗"
            print(f"  {status} {fdr_col} → {db_col}")

        return df

    except Exception as e:
        print(f"[probe] {symbol}: Error - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def main():
    args = parse_args()
    end = args.end or datetime.today().strftime("%Y-%m-%d")

    print("="*60)
    print("FDR US Stock Probe")
    print("="*60)

    # 1. StockListing 테스트
    if not args.skip_listing:
        listings = {}

        # NYSE
        df_nyse = test_stock_listing('NYSE')
        if df_nyse is not None:
            listings['NYSE'] = len(df_nyse)

        # NASDAQ
        df_nasdaq = test_stock_listing('NASDAQ')
        if df_nasdaq is not None:
            listings['NASDAQ'] = len(df_nasdaq)

        # ETF/US (지원 여부 확인)
        df_etf = test_stock_listing('ETF/US')
        if df_etf is not None:
            listings['ETF/US'] = len(df_etf)

        # Summary
        print(f"\n{'='*60}")
        print("[probe] StockListing Summary:")
        print('='*60)
        for market, count in listings.items():
            print(f"  - {market}: {count:,} symbols")

        if 'ETF/US' not in listings or listings.get('ETF/US', 0) == 0:
            print("\n[probe] ⚠️  ETF/US may not be supported. Consider alternative approaches.")

    # 2. DataReader 테스트
    test_data_reader(args.symbol, args.start, end)

    print(f"\n{'='*60}")
    print("[probe] Done.")
    print('='*60)


if __name__ == "__main__":
    main()
