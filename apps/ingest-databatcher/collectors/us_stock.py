# -*- coding: utf-8 -*-
# collectors/us_stock.py
"""
US 주식 가격 데이터 Collector (FinanceDataReader 기반)

NYSE, NASDAQ, US ETF 종목의 일별 가격 데이터(OHLCV)를 수집합니다.

작성자: DataBatcher Team
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from core.base_collector import BaseCollector
from core.db_manager import DBManager


class USStockCollector(BaseCollector):
    """
    US 주식 가격 데이터 수집기 (FinanceDataReader 기반)

    FinanceDataReader 라이브러리를 사용하여 미국 거래소(NYSE, NASDAQ) 상장 종목의
    일별 가격 데이터(OHLCV)를 수집합니다.

    Features:
    - 수정주가(Adj Close) 포함
    - FDR 컬럼 자동 매핑 (Open → open, Adj Close → adj_close 등)
    """

    category = "us_stock"

    def __init__(self, engine: Engine, table: str = "us_stock_prices"):
        """
        Initialize USStockCollector

        Args:
            engine: SQLAlchemy engine
            table: Database table name (default: "us_stock_prices")
        """
        self.engine = engine
        self.table = table

    def fetch(self, symbol: str, start, end, market: str = "NYSE") -> pd.DataFrame:
        """
        Fetch price data from FDR for a US symbol.

        Args:
            symbol: 종목코드 (예: 'AAPL', 'MSFT')
            start: 시작일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            end: 종료일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            market: 시장 구분 (NYSE/NASDAQ/ETF)

        Returns:
            DataFrame with columns:
            - symbol: 종목코드
            - date: 날짜 (datetime.date)
            - open: 시가
            - high: 고가
            - low: 저가
            - close: 종가
            - adj_close: 수정종가
            - volume: 거래량
            - market: 시장 구분 (NYSE/NASDAQ/ETF)
            - source: 데이터 출처 (fdr)

        Example:
            >>> collector = USStockCollector(engine)
            >>> df = collector.fetch('AAPL', '2024-01-01', '2024-01-31', market='NASDAQ')
            >>> print(df.columns)
            Index(['symbol', 'date', 'open', 'high', 'low', 'close',
                   'adj_close', 'volume', 'market', 'source'], dtype='object')
        """
        import FinanceDataReader as fdr

        # 날짜 포맷 변환 (date 객체 → 문자열)
        start_str = str(start) if not isinstance(start, str) else start
        end_str = str(end) if not isinstance(end, str) else end

        # FDR 데이터 수집
        df = fdr.DataReader(symbol, start=start_str, end=end_str)

        if df is None or df.empty:
            return pd.DataFrame()

        # 인덱스(Date)를 컬럼으로 변환
        df = df.reset_index()

        # 컬럼명 정규화 (FDR → DB 스키마)
        # FDR 반환: index (reset_index 후), Open, High, Low, Close, Adj Close, Volume
        # Note: reset_index() 후 인덱스가 'index' 컬럼이 됨 (Date가 아님)
        column_mapping = {
            'index': 'date',  # reset_index() 후 인덱스명
            'Date': 'date',   # fallback
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume',
        }

        # 컬럼명 변경 (존재하는 컬럼만)
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # adj_close가 없는 경우 close로 대체
        if 'adj_close' not in df.columns and 'close' in df.columns:
            df['adj_close'] = df['close']

        # 메타데이터 추가
        df['symbol'] = symbol
        df['market'] = market
        df['source'] = 'fdr'

        # 날짜를 date 타입으로 변환
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date

        # 최종 컬럼 순서
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

        # 존재하는 컬럼만 선택 (누락된 컬럼 방지)
        available = [col for col in expected if col in df.columns]
        df = df[available]

        return df

    def save(self, df: pd.DataFrame, symbol: str, mode: str = "upsert") -> int:
        """
        Save price data to database.

        Args:
            df: DataFrame with price data
            symbol: Stock symbol (KR 패턴 호환용, 실제 미사용 - df에 symbol 포함)
            mode: "upsert" (default, overwrites) or "insert_only" (preserves existing)

        Returns:
            Number of rows processed
        """
        if df is None or df.empty:
            return 0
        return DBManager.upsert_dataframe(self.engine, df, table=self.table, mode=mode)
