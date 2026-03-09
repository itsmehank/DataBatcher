# -*- coding: utf-8 -*-
# collectors/kr_etf.py
"""KRX ETF 가격 데이터 Collector (pykrx 기반)

설계 목표
- stock_prices 테이블(일봉) 스키마에 맞는 DataFrame을 생성한다.
- symbol_master.market = 'ETF' 정책을 그대로 따른다.

주의
- ETF 티커는 숫자 6자리만이 아니라 알파벳이 섞인 값도 존재할 수 있으므로 문자열로 취급한다.
- pykrx의 ETF 데이터는 주식 get_market_ohlcv와 API/컬럼 형태가 다르므로 별도 collector로 분리한다.

사용 API
- pykrx.stock.get_market_ohlcv(fromdate, todate, ticker, adjusted=True)

반환 컬럼(표준)
- symbol, date, open, high, low, close, adj_close, volume, market, source
"""

from __future__ import annotations

import pandas as pd

from core.base_collector import BaseCollector
from core.db_manager import DBManager
from core.pykrx_adapter import to_pykrx_date


class KREtfCollector(BaseCollector):
    """KRX ETF 가격 데이터 수집기 (pykrx 기반)"""

    category = "etf"

    def __init__(self, engine, table: str = "stock_prices"):
        self.engine = engine
        self.table = table

    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        """ETF OHLCV를 조회하여 프로젝트 표준 스키마로 변환한다.

        Args:
            symbol: ETF 티커
            start/end: date 객체 또는 'YYYY-MM-DD'
            market: 항상 'ETF'가 들어오는 것을 기대하지만, 호환을 위해 인자로 받음
        """
        from pykrx import stock

        start_str = to_pykrx_date(start)
        end_str = to_pykrx_date(end)

        df = stock.get_market_ohlcv(start_str, end_str, str(symbol), adjusted=True)
        if df is None or df.empty:
            return df

        df = df.copy()

        # ETF OHLCV 컬럼 매핑(확정 규칙)
        mapping = {
            "시가": "open",
            "고가": "high",
            "저가": "low",
            "종가": "close",
            "거래량": "volume",
        }
        df = df.rename(columns=mapping)

        # required columns 확인
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in ETF OHLCV: {missing}. Available={list(df.columns)}")

        # drop extra columns (NAV, 거래대금, 기초지수 등)
        keep_cols = ["open", "high", "low", "close", "volume"]
        df = df[keep_cols]

        # index(date) -> column
        df = df.reset_index()

        # pykrx returns DatetimeIndex; normalize to date
        # index name can be '날짜' or similar depending on pykrx; after reset_index it's first column
        if "date" not in df.columns:
            # 가장 첫 컬럼을 date로 간주
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "date"})

        df["date"] = pd.to_datetime(df["date"]).dt.normalize().dt.date

        # metadata
        df["symbol"] = str(symbol)
        df["market"] = "ETF"
        df["source"] = "pykrx"

        # adj_close 정책: close와 동일
        df["adj_close"] = df["close"]

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
        df = df[expected]

        return df

    def save(self, df: pd.DataFrame, symbol: str, mode: str = "upsert") -> int:
        return DBManager.upsert_dataframe(self.engine, df, table=self.table, mode=mode)
