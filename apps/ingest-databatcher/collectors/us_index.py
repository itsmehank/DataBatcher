# -*- coding: utf-8 -*-
# collectors/us_index.py
"""
US Index 가격 데이터 Collector (FinanceDataReader 기반)

S&P 500(US500), Dow Jones(DJI), NASDAQ Composite(IXIC) 지수의
일별 가격 데이터(OHLCV)를 수집합니다.
주식 collector와 달리 adj_close 컬럼이 없습니다 (지수는 수정주가 불필요).
"""
from __future__ import annotations

import logging

import pandas as pd
from core.base_collector import BaseCollector
from core.db_manager import DBManager


logger = logging.getLogger(__name__)

YF_INDEX_SYMBOL_MAP = {
    "US500": "^GSPC",
    "DJI": "^DJI",
    "IXIC": "^IXIC",
}


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

    def __init__(self, engine, table: str = "us_index_prices", source_strategy: str = "fdr"):
        self.engine = engine
        self.table = table
        self.source_strategy = source_strategy.lower()
        self.last_fetch_source: str | None = None
        self.last_fetch_note: str | None = None

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
                "US index %s: falling back to yfinance (%s)",
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

        raise ValueError(f"Unsupported US index source_strategy: {self.source_strategy}")

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
            "Volume": "volume",
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        keep_cols = ["date", "open", "high", "low", "close", "volume"]
        df = df[[col for col in keep_cols if col in df.columns]]

        df["symbol"] = symbol
        df["market"] = market
        df["source"] = source
        df["date"] = pd.to_datetime(df["date"]).dt.date

        expected = [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "market",
            "source",
        ]
        return df[expected]

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

        yf_symbol = YF_INDEX_SYMBOL_MAP.get(str(symbol))
        if not yf_symbol:
            raise ValueError(f"Unsupported US index symbol for yfinance: {symbol}")

        start_str = str(start) if not isinstance(start, str) else start
        end_str = str(end) if not isinstance(end, str) else end
        df = yf.download(yf_symbol, start=start_str, end=end_str, auto_adjust=False, progress=False)
        df = self._normalize_price_frame(df, symbol, market, source="yfinance")
        return self._clip_to_requested_range(df, start, end)

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
