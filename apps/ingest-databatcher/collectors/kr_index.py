# -*- coding: utf-8 -*-
# collectors/kr_index.py
"""
KR 지수(Index) 가격 데이터 Collector (yfinance 기반)

KOSPI(1001), KOSDAQ(2001) 등 대표 지수의 일봉 OHLCV 데이터를 수집합니다.
주식 collector와 달리 adj_close 컬럼이 없습니다 (지수는 수정주가 불필요).
"""
from __future__ import annotations

import pandas as pd
from core.base_collector import BaseCollector
from core.db_manager import DBManager


YF_INDEX_SYMBOL_MAP = {
    "1001": "^KS11",  # KOSPI
    "2001": "^KQ11",  # KOSDAQ
}


class KRIndexCollector(BaseCollector):
    """
    KR 지수 가격 데이터 수집기 (yfinance 기반)

    yfinance를 사용하여 한국 대표 지수의
    일별 가격 데이터(OHLCV)를 수집합니다.

    주식 collector와의 차이점:
    - adj_close 컬럼 없음 (지수는 수정주가 불필요)
    - yfinance ticker 사용 (1001->^KS11, 2001->^KQ11)
    - volume은 소스 단위 차이로 저장하지 않음(NULL)
    """

    category = "kr_index"

    def __init__(self, engine, table: str = "kr_index_prices"):
        self.engine = engine
        self.table = table

    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        """
        Fetch index OHLC data from yfinance.

        Args:
            symbol: 지수코드 (예: '1001' KOSPI, '2001' KOSDAQ)
            start: 시작일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            end: 종료일 (date 객체 또는 'YYYY-MM-DD' 문자열)
            market: 시장 구분 (KOSPI/KOSDAQ)

        Returns:
            DataFrame with columns:
            - symbol, date, open, high, low, close, volume, market, source
            (adj_close 없음)
        """
        import yfinance as yf

        yf_symbol = YF_INDEX_SYMBOL_MAP.get(str(symbol))
        if not yf_symbol:
            raise ValueError(f"Unsupported KR index symbol for yfinance: {symbol}")

        start_ts = pd.to_datetime(start)
        end_ts = pd.to_datetime(end)

        # yfinance end는 exclusive 이므로 +1일
        start_str = start_ts.strftime("%Y-%m-%d")
        end_exclusive = (end_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        df = yf.download(
            yf_symbol,
            start=start_str,
            end=end_exclusive,
            progress=False,
            auto_adjust=False,
            actions=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()

        # yfinance가 MultiIndex 컬럼을 반환할 수 있으므로 1차원으로 정규화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        # 컬럼 매핑 (yfinance 표준 컬럼 → 내부 스키마)
        col_map = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
        }
        df = df.rename(columns=col_map)

        # 필수 OHLC 컬럼만 유지
        required_ohlc = ['open', 'high', 'low', 'close']
        missing = [c for c in required_ohlc if c not in df.columns]
        if missing:
            raise ValueError(f"Missing OHLC columns from yfinance response: {missing}")
        df = df[required_ohlc]

        # 인덱스를 컬럼으로 변환
        df = df.reset_index()
        df.index.name = None

        # 날짜 컬럼 이름 정규화
        date_col = df.columns[0]
        if date_col != 'date':
            df = df.rename(columns={date_col: 'date'})

        # 메타데이터 추가
        df['symbol'] = symbol
        df['market'] = market
        df['source'] = 'yfinance'

        # volume은 소스 단위 불일치로 저장하지 않음
        df['volume'] = None

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
        return DBManager.upsert_dataframe(self.engine, df, table=self.table, mode=mode)
