# -*- coding: utf-8 -*-
"""
pykrx 어댑터 모듈

pykrx 라이브러리의 데이터를 DataBatcher 프로젝트 표준 형식으로 변환합니다.

주요 기능:
1. 컬럼명 매핑 (한글 → 영문)
2. 날짜 포맷 변환 (YYYY-MM-DD ↔ YYYYMMDD)
3. 종목 목록 조회 (FDR 호환 형식)

작성일: 2026-01-27
버전: 1.0
"""
from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# 컬럼 매핑 정의
# ============================================================================

# pykrx 가격 데이터 컬럼 → 프로젝트 표준 컬럼
# 실제 테스트 검증 완료 (2026-01-27)
PRICE_COLUMN_MAPPING = {
    '시가': 'open',
    '고가': 'high',
    '저가': 'low',
    '종가': 'close',
    '거래량': 'volume',
    '등락률': 'change_rate',  # 현재 미사용, FDR의 Change에 대응
}


# ============================================================================
# 컬럼 정규화 함수
# ============================================================================

def normalize_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    pykrx 가격 데이터의 한글 컬럼을 영문으로 변환

    Args:
        df: pykrx.stock.get_market_ohlcv() 반환 DataFrame
            Expected columns: 시가, 고가, 저가, 종가, 거래량, 등락률
            Expected index: DatetimeIndex (날짜)

    Returns:
        정규화된 DataFrame
        Columns: open, high, low, close, volume, change_rate
        Index: DatetimeIndex (name='date')

    Example:
        >>> from pykrx import stock
        >>> df = stock.get_market_ohlcv('20240101', '20240131', '005930')
        >>> df = normalize_price_columns(df)
        >>> print(df.columns)
        Index(['open', 'high', 'low', 'close', 'volume', 'change_rate'], dtype='object')
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    # 미매핑 컬럼 경고 (새 컬럼 추가 감지)
    unmapped = set(df.columns) - set(PRICE_COLUMN_MAPPING.keys())
    if unmapped:
        logger.warning(f"Unmapped columns detected in pykrx data: {unmapped}")
        logger.warning("Consider updating PRICE_COLUMN_MAPPING in core/pykrx_adapter.py")

    # 컬럼명 매핑
    df = df.rename(columns=PRICE_COLUMN_MAPPING)

    # 인덱스 이름 정규화
    df.index.name = 'date'

    # 필수 컬럼 존재 확인
    required = ['open', 'high', 'low', 'close', 'volume']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"Required columns missing after mapping: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    return df


# ============================================================================
# 날짜 변환 함수
# ============================================================================

def to_pykrx_date(dt: date | str) -> str:
    """
    Python date 또는 'YYYY-MM-DD' 문자열을 pykrx 형식('YYYYMMDD')으로 변환

    Args:
        dt: datetime.date 객체 또는 'YYYY-MM-DD' 형식 문자열

    Returns:
        'YYYYMMDD' 형식 문자열

    Examples:
        >>> to_pykrx_date(date(2024, 1, 1))
        '20240101'
        >>> to_pykrx_date('2024-01-01')
        '20240101'

    Raises:
        ValueError: 잘못된 날짜 형식
    """
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d').date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {dt}. Expected YYYY-MM-DD") from e
    elif not isinstance(dt, date):
        raise TypeError(f"Expected date or str, got {type(dt)}")

    return dt.strftime('%Y%m%d')


def from_pykrx_date(dt_str: str) -> date:
    """
    pykrx 날짜 형식('YYYYMMDD')을 Python date로 변환

    Args:
        dt_str: 'YYYYMMDD' 형식 문자열

    Returns:
        datetime.date 객체

    Examples:
        >>> from_pykrx_date('20240101')
        datetime.date(2024, 1, 1)

    Raises:
        ValueError: 잘못된 날짜 형식
    """
    try:
        return datetime.strptime(dt_str, '%Y%m%d').date()
    except ValueError as e:
        raise ValueError(f"Invalid pykrx date format: {dt_str}. Expected YYYYMMDD") from e


# ============================================================================
# 종목 목록 조회 함수
# ============================================================================

def fetch_krx_listing(date_str: Optional[str] = None) -> pd.DataFrame:
    """
    pykrx를 사용하여 FDR StockListing('KRX')과 동일한 구조로 종목 목록 조회

    이 함수는 다음 작업을 수행합니다:
    1. 각 시장(KOSPI, KOSDAQ, KONEX)별로 종목 코드 조회
    2. 각 종목의 종목명 조회 (개별 API 호출)
    3. 시가총액 정보를 배치로 조회하여 병합

    주의: 종목명 조회는 종목당 1회 API 호출이 필요하므로
          전체 종목(약 2,900개) 조회 시 5-10분 소요될 수 있습니다.

    Args:
        date_str: 조회 날짜 (YYYYMMDD 형식), None이면 오늘 날짜 사용

    Returns:
        DataFrame with columns:
        - Code: 종목코드 (str)
        - Name: 종목명 (str)
        - Market: 시장 구분 (KOSPI/KOSDAQ/KONEX)
        - Marcap: 시가총액 (int, 억원 단위, 없으면 NA)

    Example:
        >>> df = fetch_krx_listing()
        >>> print(len(df))
        2888
        >>> print(df.columns)
        Index(['Code', 'Name', 'Market', 'Marcap'], dtype='object')

    Raises:
        ImportError: pykrx 설치되지 않은 경우
        Exception: API 호출 실패
    """
    try:
        from pykrx import stock
    except ImportError as e:
        raise ImportError(
            "pykrx not installed. Run: pip install pykrx"
        ) from e

    # 조회 날짜 설정
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    logger.info(f"Fetching KRX listing for date: {date_str}")

    results = []
    total_symbols = 0

    # 각 시장별로 조회
    for market in ['KOSPI', 'KOSDAQ']:
        try:
            logger.info(f"  Fetching {market} symbols...")
            tickers = stock.get_market_ticker_list(date_str, market=market)
            market_count = len(tickers)
            total_symbols += market_count
            logger.info(f"  {market}: {market_count} symbols")

            # 각 종목의 종목명 조회 (개별 호출)
            for ticker in tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    results.append({
                        'Code': ticker,
                        'Name': name,
                        'Market': market,
                    })
                except Exception as e:
                    logger.warning(f"  Failed to get name for {ticker}: {e}")
                    results.append({
                        'Code': ticker,
                        'Name': '',  # 실패 시 빈 문자열
                        'Market': market,
                    })

        except Exception as e:
            logger.error(f"Failed to fetch {market} symbols: {e}")
            # 한 시장 실패해도 다른 시장은 계속 진행

    if not results:
        raise ValueError("Failed to fetch any symbols from KRX")

    logger.info(f"Total symbols fetched: {len(results)}")

    df = pd.DataFrame(results)

    # 시가총액 추가 (배치 조회)
    logger.info("Fetching market cap data...")
    try:
        marcap_df = stock.get_market_cap(date_str, market='ALL')
        # pykrx 컬럼: 종가, 시가총액, 거래량, 거래대금, 상장주식수
        marcap_df = marcap_df.rename(columns={'시가총액': 'Marcap'})

        # ticker를 기준으로 merge (인덱스가 ticker)
        df = df.merge(
            marcap_df[['Marcap']],
            left_on='Code',
            right_index=True,
            how='left'
        )
        logger.info("Market cap data merged successfully")
    except Exception as e:
        logger.warning(f"Failed to fetch market cap data: {e}")
        df['Marcap'] = pd.NA

    logger.info(f"KRX listing fetch completed: {len(df)} symbols")

    return df


# ============================================================================
# 유틸리티 함수
# ============================================================================

def validate_price_data(df: pd.DataFrame, symbol: str) -> bool:
    """
    수집된 가격 데이터의 유효성 검증

    Args:
        df: 가격 데이터 DataFrame
        symbol: 종목코드

    Returns:
        True: 유효, False: 검증 실패

    Checks:
        - DataFrame이 비어있지 않은지
        - 필수 컬럼이 존재하는지
        - 가격 데이터가 음수가 아닌지
        - 결측치가 과도하지 않은지
    """
    if df is None or df.empty:
        logger.error(f"{symbol}: DataFrame is None or empty")
        return False

    # 필수 컬럼 확인
    required = ['open', 'high', 'low', 'close', 'volume']
    missing = set(required) - set(df.columns)
    if missing:
        logger.error(f"{symbol}: Missing required columns: {missing}")
        return False

    # 가격 컬럼이 음수가 아닌지 확인
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if (df[col] < 0).any():
            logger.error(f"{symbol}: Negative values found in {col}")
            return False

    # 결측치 확인 (10% 이상이면 경고)
    na_ratio = df[required].isna().sum() / len(df)
    high_na = na_ratio[na_ratio > 0.1]
    if not high_na.empty:
        logger.warning(f"{symbol}: High NA ratio: {high_na.to_dict()}")

    return True


# ============================================================================
# 모듈 정보
# ============================================================================

def fetch_sector_classifications(date_str: Optional[str] = None) -> pd.DataFrame:
    """
    pykrx를 사용하여 KRX 업종 대분류 정보 조회 (KOSPI + KOSDAQ)

    Args:
        date_str: 조회 날짜 (YYYYMMDD 형식), None이면 오늘 날짜 사용

    Returns:
        DataFrame with columns:
        - Code: 종목코드 (str)
        - sector: 업종 대분류명 (str, 약 26개 카테고리)

    Note:
        실패 시 빈 DataFrame 반환 (non-fatal)
    """
    try:
        from pykrx import stock
    except ImportError:
        logger.warning("pykrx not installed, skipping sector classification fetch")
        return pd.DataFrame(columns=['Code', 'sector'])

    # 비거래일이면 빈 결과가 나오므로 최근 5일을 역순 탐색
    from datetime import timedelta
    if date_str is None:
        base_date = datetime.now().date()
    else:
        base_date = datetime.strptime(date_str, '%Y%m%d').date()

    results = []
    used_date = None

    for offset in range(5):
        candidate = (base_date - timedelta(days=offset)).strftime('%Y%m%d')
        logger.info(f"Trying sector classifications for date: {candidate}")
        results = []
        for market in ['KOSPI', 'KOSDAQ']:
            try:
                df = stock.get_market_sector_classifications(candidate, market)
                if df is not None and not df.empty and '업종명' in df.columns:
                    sector_df = pd.DataFrame({
                        'Code': df.index.astype(str),
                        'sector': df['업종명'].values,
                    })
                    results.append(sector_df)
                    logger.info(f"  {market}: {len(sector_df)} symbols with sector info")
            except Exception as e:
                logger.warning(f"  Failed to fetch {market} sector classifications: {e}")
        if results:
            used_date = candidate
            break

    if not results:
        logger.warning("No sector classification data fetched (tried 5 recent dates)")
        return pd.DataFrame(columns=['Code', 'sector'])

    logger.info(f"Using sector data from date: {used_date}")

    combined = pd.concat(results, ignore_index=True)
    logger.info(f"Total sector classifications: {len(combined)} symbols, {combined['sector'].nunique()} unique sectors")
    return combined


__all__ = [
    'PRICE_COLUMN_MAPPING',
    'normalize_price_columns',
    'to_pykrx_date',
    'from_pykrx_date',
    'fetch_krx_listing',
    'validate_price_data',
    'fetch_sector_classifications',
]

__version__ = '1.0.0'
__author__ = 'DataBatcher Team'
__date__ = '2026-01-27'