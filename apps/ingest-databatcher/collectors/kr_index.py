# -*- coding: utf-8 -*-
# collectors/kr_index.py
"""
KR 지수(Index) 가격 데이터 Collector (yfinance 기반)

KOSPI(1001), KOSDAQ(2001) 등 대표 지수의 일봉 OHLCV 데이터를 수집합니다.
주식 collector와 달리 adj_close 컬럼이 없습니다 (지수는 수정주가 불필요).
"""
from __future__ import annotations

import logging
import os

import pandas as pd
from core.base_collector import BaseCollector
from core.db_manager import DBManager
from core.pykrx_adapter import normalize_price_columns, to_pykrx_date


YF_INDEX_SYMBOL_MAP = {
    "1001": "^KS11",  # KOSPI
    "2001": "^KQ11",  # KOSDAQ
}

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        engine,
        table: str = "kr_index_prices",
        source_strategy: str = "yfinance",
    ):
        self.engine = engine
        self.table = table
        self.source_strategy = source_strategy
        self.last_fetch_source: str | None = None
        self.last_fetch_note: str | None = None
        self._pykrx_session = None

    def fetch(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        self.last_fetch_source = None
        self.last_fetch_note = None

        if self.source_strategy == "pykrx_then_yfinance":
            try:
                df_pykrx = self._fetch_via_pykrx(symbol, start, end, market)
                if df_pykrx is not None and not df_pykrx.empty:
                    validated = self.validate(df_pykrx)
                    if validated is not None and not validated.empty:
                        self.last_fetch_source = "pykrx"
                        return df_pykrx
                    self.last_fetch_note = "pykrx returned only invalid rows after validation"
                else:
                    self.last_fetch_note = "pykrx returned no rows"
            except Exception as exc:
                self.last_fetch_note = f"pykrx failed: {exc}"

            logger.warning(
                "KR index %s: falling back to yfinance (%s)",
                symbol,
                self.last_fetch_note,
            )

        df_yf = self._fetch_via_yfinance(symbol, start, end, market)
        self.last_fetch_source = "yfinance"
        return df_yf

    def _fetch_via_pykrx(self, symbol: str, start, end, market: str) -> pd.DataFrame:
        from pykrx import stock

        self._ensure_pykrx_logged_in()

        df = stock.get_index_ohlcv(
            to_pykrx_date(pd.to_datetime(start).date()),
            to_pykrx_date(pd.to_datetime(end).date()),
            str(symbol),
            name_display=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        df = df[["시가", "고가", "저가", "종가", "거래량"]].copy()
        df = normalize_price_columns(df)
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["symbol"] = symbol
        df["market"] = market
        df["source"] = "pykrx"

        expected = [
            "symbol", "date", "open", "high", "low", "close",
            "volume", "market", "source",
        ]
        return df[expected]

    def _fetch_via_yfinance(self, symbol: str, start, end, market: str) -> pd.DataFrame:
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

    def _ensure_pykrx_logged_in(self) -> None:
        if self._pykrx_session is not None:
            return

        login_id = os.getenv("KRX_LOGIN_ID")
        login_password = os.getenv("KRX_LOGIN_PASSWORD")
        if not login_id or not login_password:
            raise RuntimeError("KRX_LOGIN_ID/KRX_LOGIN_PASSWORD not set")

        import requests
        from pykrx.website.comm import webio

        session = requests.Session()

        def _session_post_read(self, **params):
            return session.post(self.url, headers=self.headers, data=params, timeout=15)

        def _session_get_read(self, **params):
            return session.get(self.url, headers=self.headers, params=params, timeout=15)

        webio.Post.read = _session_post_read
        webio.Get.read = _session_get_read

        login_page = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
        login_jsp = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc"
        login_url = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        session.get(login_page, headers={"User-Agent": user_agent}, timeout=15)
        session.get(
            login_jsp,
            headers={"User-Agent": user_agent, "Referer": login_page},
            timeout=15,
        )

        payload = {
            "mbrNm": "",
            "telNo": "",
            "di": "",
            "certType": "",
            "mbrId": login_id,
            "pw": login_password,
        }
        headers = {"User-Agent": user_agent, "Referer": login_page}

        response = session.post(login_url, data=payload, headers=headers, timeout=15)
        data = response.json()
        error_code = data.get("_error_code", "")

        if error_code == "CD011":
            payload["skipDup"] = "Y"
            response = session.post(login_url, data=payload, headers=headers, timeout=15)
            data = response.json()
            error_code = data.get("_error_code", "")

        if error_code != "CD001":
            raise RuntimeError(f"KRX login failed: {error_code or 'unknown'}")

        self._pykrx_session = session

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
