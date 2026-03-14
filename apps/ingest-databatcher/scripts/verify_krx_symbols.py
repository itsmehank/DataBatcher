#!/usr/bin/env python3
"""
Verify if symbols exist in KRX listing from FinanceDataReader
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import FinanceDataReader as fdr
import pandas as pd

# Failed symbols
FAILED_SYMBOLS = [
    "0004V0",
    "0004Y0",
    "0007C0",
    "0008Z0",
    "0009K0",
    "0010V0",
    "0013V0",
]


def main():
    print("=" * 80)
    print("Verifying Failed Symbols Against KRX Listing")
    print("=" * 80)

    # Get full KRX listing from FDR
    print("\nFetching current KRX listing from FinanceDataReader...")
    try:
        krx_all = fdr.StockListing("KRX")
        print(f"✅ Total symbols in KRX: {len(krx_all)}")
    except Exception as e:
        print(f"❌ Failed to fetch KRX listing: {e}")
        return

    # Check each failed symbol
    print("\n" + "=" * 80)
    print("Checking Failed Symbols in KRX Listing")
    print("=" * 80)

    for symbol in FAILED_SYMBOLS:
        matches = krx_all[krx_all["Code"] == symbol]

        if matches.empty:
            print(f"\n❌ {symbol}: NOT FOUND in current KRX listing")
            print(f"   → This symbol may be delisted or invalid")
        else:
            row = matches.iloc[0]
            print(f"\n✅ {symbol}: FOUND in KRX listing")
            print(f"   Name: {row['Name']}")
            print(f"   Market: {row['Market']}")
            print(f"   Sector: {row.get('Sector', 'N/A')}")
            print(f"   Industry: {row.get('Industry', 'N/A')}")

    # Analyze symbol pattern
    print("\n\n" + "=" * 80)
    print("Symbol Pattern Analysis")
    print("=" * 80)

    # Check if there are any other symbols with similar suffixes
    suffix_pattern = krx_all[krx_all["Code"].str.match(r".*[A-Z]\d$")]
    print(f"\nTotal symbols with letter+digit suffix (e.g., V0, Y0): {len(suffix_pattern)}")

    if len(suffix_pattern) > 0:
        print(f"\nSample symbols with similar pattern:")
        print(suffix_pattern.head(10)[["Code", "Name", "Market"]])

    # Check failed symbols in the pattern
    failed_in_pattern = suffix_pattern[suffix_pattern["Code"].isin(FAILED_SYMBOLS)]
    print(f"\n\nFailed symbols found in suffix pattern: {len(failed_in_pattern)}/{len(FAILED_SYMBOLS)}")

    # Final diagnosis
    print("\n\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    found_count = sum(1 for s in FAILED_SYMBOLS if s in krx_all["Code"].values)

    if found_count == 0:
        print("\n⚠️  None of the failed symbols are in current KRX listing")
        print("\n   Likely causes:")
        print("   1. These symbols were recently delisted")
        print("   2. Symbol codes in symbol_master are outdated")
        print("   3. These are test/invalid symbols")
        print("\n   ✅ RECOMMENDATION:")
        print("   - Run: python scripts/sync_symbol_master.py")
        print("   - This will mark these symbols as DELISTED")
    elif found_count == len(FAILED_SYMBOLS):
        print(f"\n⚠️  All {found_count} failed symbols ARE in KRX listing")
        print("\n   Likely causes:")
        print("   1. Yahoo Finance doesn't have data for these symbols")
        print("   2. These are newly listed (data not yet available)")
        print("   3. These are SPACs or special purpose companies")
        print("\n   ✅ RECOMMENDATION:")
        print("   - Keep symbols in DB (they're valid)")
        print("   - Data will be collected when available")
        print("   - Consider using alternative data sources for these symbols")
    else:
        print(f"\n⚠️  Mixed results: {found_count}/{len(FAILED_SYMBOLS)} in KRX listing")
        print("\n   ✅ RECOMMENDATION:")
        print("   - Run: python scripts/sync_symbol_master.py")
        print("   - This will update the status of delisted symbols")


if __name__ == "__main__":
    main()