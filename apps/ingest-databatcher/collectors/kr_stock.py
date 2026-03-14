# -*- coding: utf-8 -*-
# collectors/kr_stock.py
"""
KRX 주식 가격 데이터 Collector (pykrx 기반)

변경 이력:
- 2026-01-27: FDR에서 pykrx로 전환
- 기존: FinanceDataReader 사용
- 현재: pykrx 사용

작성자: DataBatcher Team
"""
from __future__ import annotations

import pandas as pd
from core.base_collector import BaseCollector
from core.db_manager import DBManager


class KRStockCollector(BaseCollector):
    """
    KRX 주식 가격 데이터 수집기 (pykrx 기반)

    pykrx 라이브러리를 사용하여 한국거래소(KRX) 상장 종목의
    일별 가격 데이터(OHLCV)를 수집합니다.

    Features:
    - 수정주가 자동 적용 (adjusted=True)
    - FDR 호환 데이터 형식 출력
    - 컬럼 자동 매핑 (한글 → 영문)
    """

    category = "stock"

    def __init__(self, engine, table: str = "stock_prices"):
        """
        Initialize KRStockCollector

        Args:
            engine: SQLAlchemy engine
            table: Database table name (default: "stock_prices")
        """
        self.engine = engine
        self.table = table

    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        """
        Fetch price data from pykrx for a KRX symbol.

        Args:
            symbol: 종목코드 (예: '005930')
            start: 시작일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            end: 종료일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            market: 시장 구분 (KOSPI/KOSDAQ/KONEX) - 필수

        Returns:
            DataFrame with columns:
            - symbol: 종목코드
            - date: 날짜 (datetime.date)
            - open: 시가
            - high: 고가
            - low: 저가
            - close: 종가
            - adj_close: 수정종가 (adjusted=True이므로 close와 동일)
            - volume: 거래량
            - market: 시장 구분 (market 파라미터 값)
            - source: 데이터 출처 (pykrx)

        Example:
            >>> collector = KRStockCollector(engine)
            >>> df = collector.fetch('005930', '2024-01-01', '2024-01-31', market='KOSPI')
            >>> print(df.columns)
            Index(['symbol', 'date', 'open', 'high', 'low', 'close',
                   'adj_close', 'volume', 'market', 'source'], dtype='object')
        """
        from pykrx import stock
        from core.pykrx_adapter import to_pykrx_date, normalize_price_columns

        # 날짜 포맷 변환 (YYYY-MM-DD → YYYYMMDD)
        start_str = to_pykrx_date(start)
        end_str = to_pykrx_date(end)

        # pykrx 데이터 수집 (adjusted=True: 수정주가 사용)
        df = stock.get_market_ohlcv(start_str, end_str, symbol, adjusted=True)

        if df is None or df.empty:
            return df

        # 컬럼명 정규화 (한글 → 영문)
        # 시가, 고가, 저가, 종가, 거래량, 등락률 → open, high, low, close, volume, change_rate
        df = normalize_price_columns(df)

        # adj_close 컬럼 추가
        # adjusted=True로 조회했으므로 close가 이미 수정주가
        # FDR 호환을 위해 adj_close 컬럼 추가
        df['adj_close'] = df['close']

        # change_rate 제거 (현재 미사용)
        if 'change_rate' in df.columns:
            df = df.drop(columns=['change_rate'])

        # 인덱스를 컬럼으로 변환
        df = df.reset_index()

        # 메타데이터 추가
        df['symbol'] = symbol
        df['market'] = market
        df['source'] = 'pykrx'

        # 날짜를 date 타입으로 변환
        df['date'] = pd.to_datetime(df['date']).dt.date

        # 최종 컬럼 순서 (FDR 호환)
        expected = [
            'symbol',
            'date',
            'open',
            'high',
            'low',
            'close',
            'adj_close',
            'volume',
            'market',
            'source',
        ]

        # 컬럼 순서 정렬
        df = df[expected]

        return df

    def save(self, df: pd.DataFrame, symbol: str, mode: str = "upsert") -> int:
        """
        Save price data to database.

        Args:
            df: DataFrame with price data
            symbol: Stock symbol
            mode: "upsert" (default, overwrites) or "insert_only" (preserves existing)

        Returns:
            Number of rows processed
        """
        return DBManager.upsert_dataframe(self.engine, df, table=self.table, mode=mode)