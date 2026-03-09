# -*- coding: utf-8 -*-
# collectors/us_index.py
"""
US Index 가격 데이터 Collector (FinanceDataReader 기반)

S&P 500(US500), Dow Jones(DJI), NASDAQ Composite(IXIC) 지수의
일별 가격 데이터(OHLCV)를 수집합니다.
주식 collector와 달리 adj_close 컬럼이 없습니다 (지수는 수정주가 불필요).
"""
from __future__ import annotations

import pandas as pd
from core.base_collector import BaseCollector
from core.db_manager import DBManager


class USIndexCollector(BaseCollector):
    """
    US Index 가격 데이터 수집기 (FinanceDataReader 기반)

    FinanceDataReader를 사용하여 미국 주요 지수의
    일별 가격 데이터(OHLCV)를 수집합니다.

    주식 collector와의 차이점:
    - adj_close 컬럼 없음 (지수는 수정주가 불필요)
    - FDR DataReader()로 지수 데이터 조회 (US500 → ^GSPC 등)
    """

    category = "us_index"

    def __init__(self, engine, table: str = "us_index_prices"):
        self.engine = engine
        self.table = table

    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        """
        Fetch index OHLCV data from FinanceDataReader.

        Args:
            symbol: FDR 지수 심볼 (예: 'US500', 'DJI', 'IXIC')
            start: 시작일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            end: 종료일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            market: 시장 구분 (SP500/DJI/IXIC)

        Returns:
            DataFrame with columns:
            - symbol, date, open, high, low, close, volume, market, source
            (adj_close 없음)
        """
        import FinanceDataReader as fdr

        start_str = str(start) if not isinstance(start, str) else start
        end_str = str(end) if not isinstance(end, str) else end

        df = fdr.DataReader(symbol, start=start_str, end=end_str)

        if df is None or df.empty:
            return pd.DataFrame()

        # 인덱스(Date)를 컬럼으로 변환
        df = df.reset_index()

        # 컬럼명 정규화 (FDR → DB 스키마)
        column_mapping = {
            'index': 'date',
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Adj Close 및 기타 불필요 컬럼 제거
        keep_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        extra_cols = [c for c in df.columns if c not in keep_cols]
        if extra_cols:
            df = df.drop(columns=extra_cols)

        # 메타데이터 추가
        df['symbol'] = symbol
        df['market'] = market
        df['source'] = 'fdr'

        # 날짜를 date 타입으로 변환
        df['date'] = pd.to_datetime(df['date']).dt.date

        # 최종 컬럼 순서
        expected = [
            'symbol', 'date', 'open', 'high', 'low', 'close',
            'volume', 'market', 'source',
        ]
        df = df[expected]

        return df

    def save(self, df: pd.DataFrame, symbol: str, mode: str = "upsert") -> int:
        """
        Save index price data to database.

        Args:
            df: DataFrame with price data
            symbol: Index symbol
            mode: "upsert" (default) or "insert_only"

        Returns:
            Number of rows processed
        """
        if df is None or df.empty:
            return 0
        return DBManager.upsert_dataframe(self.engine, df, table=self.table, mode=mode)
