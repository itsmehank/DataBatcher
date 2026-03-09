#!/usr/bin/env python3
"""
Test script to diagnose why certain symbols fail in bulk_update.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import FinanceDataReader as fdr
from datetime import datetime

# Failed symbols from the log
FAILED_SYMBOLS = [
    ("0004V0", "엔비알모션"),
    ("0004Y0", "디비금융제14호스팩"),
    ("0007C0", "아크릴"),
    ("0008Z0", "에스엔시스"),
    ("0009K0", "에임드바이오"),
    ("0010V0", "제이피아이헬스케어"),
    ("0013V0", "삼진식품"),
]

# Sample successful symbols for comparison
SUCCESS_SYMBOLS = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("005380", "현대차"),
]


def test_symbol(symbol: str, name: str, start="2024-01-01", end="2024-12-31"):
    """Test fetching data for a single symbol"""
    print(f"\n{'='*70}")
    print(f"Testing: {symbol} ({name})")
    print(f"{'='*70}")

    try:
        df = fdr.DataReader(symbol, start=start, end=end)

        if df is None:
            print("❌ Result: None returned")
            return False
        elif df.empty:
            print("❌ Result: Empty DataFrame")
            return False
        else:
            print(f"✅ Result: Success - {len(df)} rows")
            print(f"   Date range: {df.index.min()} to {df.index.max()}")
            print(f"   Columns: {list(df.columns)}")
            print(f"\n   First 3 rows:")
            print(df.head(3))
            return True

    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("DataBatcher Symbol Collection Test")
    print("=" * 70)
    print(f"Test period: 2024-01-01 to 2024-12-31")
    print(f"Failed symbols: {len(FAILED_SYMBOLS)}")
    print(f"Success symbols (control): {len(SUCCESS_SYMBOLS)}")

    # Test successful symbols first (control group)
    print("\n\n" + "=" * 70)
    print("CONTROL GROUP: Testing known successful symbols")
    print("=" * 70)

    success_results = []
    for symbol, name in SUCCESS_SYMBOLS:
        result = test_symbol(symbol, name)
        success_results.append((symbol, name, result))

    # Test failed symbols
    print("\n\n" + "=" * 70)
    print("TEST GROUP: Testing previously failed symbols")
    print("=" * 70)

    failed_results = []
    for symbol, name in FAILED_SYMBOLS:
        result = test_symbol(symbol, name)
        failed_results.append((symbol, name, result))

    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nControl Group (Expected Success):")
    for symbol, name, result in success_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {symbol} ({name})")

    print("\nTest Group (Previously Failed):")
    for symbol, name, result in failed_results:
        status = "✅ NOW OK" if result else "❌ STILL FAILS"
        print(f"  {status}  {symbol} ({name})")

    # Analysis
    control_pass = sum(1 for _, _, r in success_results if r)
    test_pass = sum(1 for _, _, r in failed_results if r)

    print(f"\nControl pass rate: {control_pass}/{len(success_results)}")
    print(f"Test pass rate: {test_pass}/{len(failed_results)}")

    # Check if there's a pattern in failed symbols
    print("\n" + "=" * 70)
    print("PATTERN ANALYSIS")
    print("=" * 70)

    still_failing = [symbol for symbol, name, result in failed_results if not result]
    if still_failing:
        print("\nStill failing symbols:")
        for symbol in still_failing:
            # Analyze symbol pattern
            has_letter_suffix = any(c.isalpha() for c in symbol[-2:])
            print(f"  - {symbol}: ", end="")
            if has_letter_suffix:
                print(f"Has letter suffix: {symbol[-2:]}")
            else:
                print("No obvious pattern")

        print("\n💡 DIAGNOSIS:")
        print("   All failed symbols have letter suffixes (V0, Y0, C0, Z0, K0)")
        print("   These may be:")
        print("   - Delisted or suspended stocks")
        print("   - SPACs or special purpose companies")
        print("   - Stocks not available in Yahoo Finance data source")
        print("   - Incorrectly formatted symbol codes in symbol_master")

        print("\n✅ RECOMMENDATION:")
        print("   1. Check if these symbols are ACTIVE in the market")
        print("   2. Verify symbol codes in symbol_master table")
        print("   3. Consider marking these as DELISTED if they're no longer trading")
        print("   4. The 93/100 success rate (93%) is acceptable for bulk collection")
    else:
        print("✅ All symbols now working!")


if __name__ == "__main__":
    main()