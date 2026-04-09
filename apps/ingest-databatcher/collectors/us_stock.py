# -*- coding: utf-8 -*-
# collectors/us_stock.py
"""
US 주식 가격 데이터 Collector (FinanceDataReader 기반)

NYSE, NASDAQ, US ETF 종목의 일별 가격 데이터(OHLCV)를 수집합니다.

작성자: DataBatcher Team
"""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy.engine import Engine

from core.base_collector import BaseCollector
from core.db_manager import DBManager


logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        engine: Engine,
        table: str = "us_stock_prices",
        source_strategy: str = "fdr",
    ):
        """
        Initialize USStockCollector

        Args:
            engine: SQLAlchemy engine
            table: Database table name (default: "us_stock_prices")
        """
        self.engine = engine
        self.table = table
        self.source_strategy = source_strategy.lower()
        self.last_fetch_source: str | None = None
        self.last_fetch_note: str | None = None

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
        self.last_fetch_source = None
        self.last_fetch_note = None

        if self.source_strategy == "fdr_then_yfinance":
            try:
                df_fdr = self._fetch_via_fdr(symbol, start, end, market)
                if df_fdr is not None and not df_fdr.empty:
                    self.last_fetch_source = "fdr"
                    return df_fdr
                self.last_fetch_note = "fdr returned no rows"
            except Exception as exc:
                self.last_fetch_note = f"fdr failed: {exc}"

            logger.warning(
                "US stock %s: falling back to yfinance (%s)",
                symbol,
                self.last_fetch_note,
            )
            df_yf = self._fetch_via_yfinance(symbol, start, end, market)
            self.last_fetch_source = "yfinance"
            return df_yf

        if self.source_strategy == "fdr":
            df_fdr = self._fetch_via_fdr(symbol, start, end, market)
            self.last_fetch_source = "fdr"
            return df_fdr

        if self.source_strategy == "yfinance":
            df_yf = self._fetch_via_yfinance(symbol, start, end, market)
            self.last_fetch_source = "yfinance"
            return df_yf

        raise ValueError(f"Unsupported US stock source_strategy: {self.source_strategy}")

    def _normalize_price_frame(
        self,
        df: pd.DataFrame | None,
        symbol: str,
        market: str,
        source: str,
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(col[0]) for col in df.columns]

        df = df.reset_index()

        column_mapping = {
            "index": "date",
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        if "adj_close" not in df.columns and "close" in df.columns:
            df["adj_close"] = df["close"]

        df["symbol"] = symbol
        df["market"] = market
        df["source"] = source

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        expected = [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
            "market",
            "source",
        ]
        available = [col for col in expected if col in df.columns]
        return df[available]

    def _clip_to_requested_range(self, df: pd.DataFrame, start, end) -> pd.DataFrame:
        if df is None or df.empty or "date" not in df.columns:
            return df

        start_d = pd.to_datetime(start).date()
        end_d = pd.to_datetime(end).date()
        return df[(df["date"] >= start_d) & (df["date"] <= end_d)].copy()

    def _fetch_via_fdr(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        import FinanceDataReader as fdr

        start_str = str(start) if not isinstance(start, str) else start
        end_str = str(end) if not isinstance(end, str) else end
        df = fdr.DataReader(symbol, start=start_str, end=end_str)
        df = self._normalize_price_frame(df, symbol, market, source="fdr")
        return self._clip_to_requested_range(df, start, end)

    def _fetch_via_yfinance(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        import yfinance as yf

        start_str = str(start) if not isinstance(start, str) else start
        end_str = str(end) if not isinstance(end, str) else end
        df = yf.download(symbol, start=start_str, end=end_str, auto_adjust=False, progress=False)
        df = self._normalize_price_frame(df, symbol, market, source="yfinance")
        return self._clip_to_requested_range(df, start, end)

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
