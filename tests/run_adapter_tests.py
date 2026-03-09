#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pykrx_adapter 간단한 테스트 실행기 (pytest 없이)
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from core.pykrx_adapter import (
    PRICE_COLUMN_MAPPING,
    normalize_price_columns,
    to_pykrx_date,
    from_pykrx_date,
    validate_price_data,
)


def test_column_mapping():
    """컬럼 매핑 테스트"""
    assert '시가' in PRICE_COLUMN_MAPPING
    assert PRICE_COLUMN_MAPPING['시가'] == 'open'
    assert PRICE_COLUMN_MAPPING['거래량'] == 'volume'
    print("✅ PASS: 컬럼 매핑 상수")


def test_normalize():
    """컬럼 정규화 테스트"""
    df = pd.DataFrame({
        '시가': [100], '고가': [110], '저가': [90],
        '종가': [105], '거래량': [1000], '등락률': [5.0],
    })
    df.index = pd.date_range('2024-01-01', periods=1)

    result = normalize_price_columns(df)
    assert 'open' in result.columns
    assert 'close' in result.columns
    assert '시가' not in result.columns
    assert result.index.name == 'date'
    print("✅ PASS: 컬럼 정규화")


def test_date_conversion():
    """날짜 변환 테스트"""
    assert to_pykrx_date('2024-01-01') == '20240101'
    assert from_pykrx_date('20240101') == date(2024, 1, 1)

    # 왕복 변환
    original = date(2024, 6, 15)
    converted = to_pykrx_date(original)
    back = from_pykrx_date(converted)
    assert back == original
    print("✅ PASS: 날짜 변환")


def test_validation():
    """데이터 검증 테스트"""
    valid_df = pd.DataFrame({
        'open': [100], 'high': [110], 'low': [90],
        'close': [105], 'volume': [1000],
    })
    assert validate_price_data(valid_df, '005930') is True

    empty_df = pd.DataFrame()
    assert validate_price_data(empty_df, '005930') is False

    assert validate_price_data(None, '005930') is False
    print("✅ PASS: 데이터 검증")


def main():
    print("="*80)
    print("pykrx_adapter 단위 테스트 실행")
    print("="*80)
    print()

    tests = [
        test_column_mapping,
        test_normalize,
        test_date_conversion,
        test_validation,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {test_func.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {test_func.__name__}")
            print(f"   Error: {e}")
            failed += 1

    print()
    print("="*80)
    print(f"결과: {passed}/{len(tests)} 통과, {failed}/{len(tests)} 실패")
    print("="*80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())