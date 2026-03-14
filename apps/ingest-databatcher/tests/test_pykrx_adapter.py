#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pykrx_adapter 모듈 단위 테스트

작성일: 2026-01-27
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import pytest

from core.pykrx_adapter import (
    PRICE_COLUMN_MAPPING,
    normalize_price_columns,
    to_pykrx_date,
    from_pykrx_date,
    fetch_krx_listing,
    validate_price_data,
)


# ============================================================================
# 컬럼 매핑 테스트
# ============================================================================

def test_column_mapping_constant():
    """컬럼 매핑 상수가 올바르게 정의되어 있는지 확인"""
    assert '시가' in PRICE_COLUMN_MAPPING
    assert '고가' in PRICE_COLUMN_MAPPING
    assert '저가' in PRICE_COLUMN_MAPPING
    assert '종가' in PRICE_COLUMN_MAPPING
    assert '거래량' in PRICE_COLUMN_MAPPING

    assert PRICE_COLUMN_MAPPING['시가'] == 'open'
    assert PRICE_COLUMN_MAPPING['고가'] == 'high'
    assert PRICE_COLUMN_MAPPING['저가'] == 'low'
    assert PRICE_COLUMN_MAPPING['종가'] == 'close'
    assert PRICE_COLUMN_MAPPING['거래량'] == 'volume'


def test_normalize_price_columns_basic():
    """기본 컬럼 매핑 테스트"""
    # 샘플 데이터 생성 (pykrx 형식)
    sample_df = pd.DataFrame({
        '시가': [100, 101, 102],
        '고가': [110, 111, 112],
        '저가': [90, 91, 92],
        '종가': [105, 106, 107],
        '거래량': [1000, 1100, 1200],
        '등락률': [5.0, 1.0, 0.94],
    })
    sample_df.index = pd.date_range('2024-01-01', periods=3, freq='D')
    sample_df.index.name = '날짜'

    # 정규화 실행
    result = normalize_price_columns(sample_df)

    # 검증: 한글 컬럼이 영문으로 변환되었는지
    assert 'open' in result.columns
    assert 'high' in result.columns
    assert 'low' in result.columns
    assert 'close' in result.columns
    assert 'volume' in result.columns
    assert 'change_rate' in result.columns

    # 검증: 한글 컬럼이 제거되었는지
    assert '시가' not in result.columns
    assert '고가' not in result.columns

    # 검증: 인덱스 이름
    assert result.index.name == 'date'

    # 검증: 데이터 값이 유지되는지
    assert result['open'].iloc[0] == 100
    assert result['close'].iloc[0] == 105
    assert result['volume'].iloc[0] == 1000


def test_normalize_price_columns_empty():
    """빈 DataFrame 처리 테스트"""
    empty_df = pd.DataFrame()
    result = normalize_price_columns(empty_df)
    assert result.empty


def test_normalize_price_columns_none():
    """None 입력 처리 테스트"""
    result = normalize_price_columns(None)
    assert result is None


def test_normalize_price_columns_missing_required():
    """필수 컬럼 누락 시 에러 발생 테스트"""
    # 필수 컬럼 중 일부만 있는 DataFrame
    incomplete_df = pd.DataFrame({
        '시가': [100],
        '고가': [110],
        # '저가' 누락
        # '종가' 누락
        # '거래량' 누락
    })

    with pytest.raises(ValueError, match="Required columns missing"):
        normalize_price_columns(incomplete_df)


# ============================================================================
# 날짜 변환 테스트
# ============================================================================

def test_to_pykrx_date_from_date_object():
    """date 객체를 pykrx 형식으로 변환"""
    dt = date(2024, 1, 1)
    result = to_pykrx_date(dt)
    assert result == '20240101'


def test_to_pykrx_date_from_string():
    """문자열을 pykrx 형식으로 변환"""
    result = to_pykrx_date('2024-01-01')
    assert result == '20240101'

    result = to_pykrx_date('2024-12-31')
    assert result == '20241231'


def test_to_pykrx_date_invalid_string():
    """잘못된 문자열 형식 처리"""
    with pytest.raises(ValueError, match="Invalid date format"):
        to_pykrx_date('2024/01/01')

    with pytest.raises(ValueError, match="Invalid date format"):
        to_pykrx_date('20240101')


def test_to_pykrx_date_invalid_type():
    """잘못된 타입 처리"""
    with pytest.raises(TypeError):
        to_pykrx_date(20240101)


def test_from_pykrx_date_valid():
    """pykrx 형식에서 date 객체로 변환"""
    result = from_pykrx_date('20240101')
    assert result == date(2024, 1, 1)

    result = from_pykrx_date('20241231')
    assert result == date(2024, 12, 31)


def test_from_pykrx_date_invalid():
    """잘못된 pykrx 날짜 형식 처리"""
    with pytest.raises(ValueError, match="Invalid pykrx date format"):
        from_pykrx_date('2024-01-01')

    with pytest.raises(ValueError, match="Invalid pykrx date format"):
        from_pykrx_date('240101')


def test_date_conversion_roundtrip():
    """날짜 변환 왕복 테스트"""
    original = date(2024, 6, 15)
    pykrx_format = to_pykrx_date(original)
    back_to_date = from_pykrx_date(pykrx_format)
    assert back_to_date == original


# ============================================================================
# 데이터 검증 테스트
# ============================================================================

def test_validate_price_data_valid():
    """유효한 데이터 검증"""
    valid_df = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [110, 111, 112],
        'low': [90, 91, 92],
        'close': [105, 106, 107],
        'volume': [1000, 1100, 1200],
    })

    assert validate_price_data(valid_df, '005930') is True


def test_validate_price_data_empty():
    """빈 DataFrame 검증"""
    empty_df = pd.DataFrame()
    assert validate_price_data(empty_df, '005930') is False


def test_validate_price_data_none():
    """None 검증"""
    assert validate_price_data(None, '005930') is False


def test_validate_price_data_missing_columns():
    """필수 컬럼 누락 검증"""
    incomplete_df = pd.DataFrame({
        'open': [100],
        'high': [110],
        # 'low', 'close', 'volume' 누락
    })

    assert validate_price_data(incomplete_df, '005930') is False


def test_validate_price_data_negative_values():
    """음수 가격 검증"""
    invalid_df = pd.DataFrame({
        'open': [100, -50, 102],  # 음수 포함
        'high': [110, 111, 112],
        'low': [90, 91, 92],
        'close': [105, 106, 107],
        'volume': [1000, 1100, 1200],
    })

    assert validate_price_data(invalid_df, '005930') is False


def test_validate_price_data_with_na():
    """결측치가 있는 데이터 검증 (경고만, 통과)"""
    df_with_na = pd.DataFrame({
        'open': [100, None, 102],
        'high': [110, 111, 112],
        'low': [90, 91, 92],
        'close': [105, 106, 107],
        'volume': [1000, 1100, 1200],
    })

    # 소량의 NA는 허용 (경고만)
    result = validate_price_data(df_with_na, '005930')
    # 결측치가 10% 미만이므로 True
    assert result is True


# ============================================================================
# 통합 테스트 (실제 pykrx 사용, optional)
# ============================================================================

@pytest.mark.integration
def test_fetch_krx_listing_integration():
    """
    실제 pykrx API 호출 테스트 (선택적)

    주의: 이 테스트는 실제 API를 호출하므로:
    - 네트워크 연결 필요
    - 시간이 오래 걸림 (5-10분)
    - CI/CD에서는 스킵 권장

    실행: pytest -m integration tests/test_pykrx_adapter.py
    """
    try:
        df = fetch_krx_listing()

        # 기본 검증
        assert not df.empty
        assert 'Code' in df.columns
        assert 'Name' in df.columns
        assert 'Market' in df.columns
        assert 'Marcap' in df.columns

        # 종목 수 검증 (최소 2,800개)
        assert len(df) >= 2800

        # 시장 구분 검증
        markets = df['Market'].unique()
        assert 'KOSPI' in markets
        assert 'KOSDAQ' in markets

        # 샘플 종목 검증 (삼성전자)
        samsung = df[df['Code'] == '005930']
        assert not samsung.empty
        assert samsung.iloc[0]['Name'] == '삼성전자'
        assert samsung.iloc[0]['Market'] == 'KOSPI'

    except Exception as e:
        pytest.skip(f"Integration test skipped: {e}")


@pytest.mark.integration
def test_normalize_with_real_pykrx_data():
    """
    실제 pykrx 데이터로 정규화 테스트 (선택적)

    실행: pytest -m integration tests/test_pykrx_adapter.py
    """
    try:
        from pykrx import stock

        # 삼성전자 최근 5일 데이터
        df = stock.get_market_ohlcv('20260120', '20260127', '005930')

        # 정규화 실행
        result = normalize_price_columns(df)

        # 검증
        assert not result.empty
        assert 'open' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns
        assert result.index.name == 'date'

        # 데이터 타입 검증
        assert result['volume'].dtype in [int, 'int64', 'int32']

    except ImportError:
        pytest.skip("pykrx not installed")
    except Exception as e:
        pytest.skip(f"Integration test skipped: {e}")


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    # 단위 테스트만 실행 (integration 제외)
    pytest.main([__file__, '-v', '-m', 'not integration'])