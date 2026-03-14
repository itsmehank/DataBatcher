# -*- coding: utf-8 -*-
"""collectors/crypto_binance.py

Binance Spot(USDT) 일봉(1d) 데이터 Collector.

- Spot only
- quote=USDT only (필터는 상위 레이어에서)
- interval=1d
- date는 UTC date (kline open time 기준)
- volume은 quoteAssetVolume을 사용하여 volume_quote에 저장

이 모듈은 '수집(fetch)'만 담당합니다.
저장(DB upsert/insert_only) 및 지표 계산은 scripts/* 에서 수행합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

import pandas as pd
import requests

from core.rate_limiter import RateLimiter


@dataclass(frozen=True)
class BinanceClientConfig:
    base_url: str = "https://api.binance.com"
    timeout_sec: float = 20.0
    requests_per_second: float = 8.0


class BinanceCryptoCollector:
    category = "crypto"

    def __init__(self, cfg: BinanceClientConfig | None = None):
        self.cfg = cfg or BinanceClientConfig()
        self._limiter = RateLimiter(self.cfg.requests_per_second)

    def fetch_exchange_info(self) -> dict[str, Any]:
        self._limiter.acquire()
        url = f"{self.cfg.base_url}/api/v3/exchangeInfo"
        r = requests.get(url, timeout=self.cfg.timeout_sec)
        r.raise_for_status()
        return r.json()

    def list_spot_usdt_symbols(self) -> list[dict[str, str]]:
        """Return list of dicts: {symbol, base_asset, quote_asset, status} for spot+TRADING+USDT."""
        data = self.fetch_exchange_info()
        out: list[dict[str, str]] = []
        for s in data.get("symbols") or []:
            if s.get("isSpotTradingAllowed") is not True:
                continue
            if s.get("status") != "TRADING":
                continue
            if s.get("quoteAsset") != "USDT":
                continue
            out.append(
                {
                    "symbol": str(s.get("symbol")),
                    "base_asset": str(s.get("baseAsset")),
                    "quote_asset": str(s.get("quoteAsset")),
                    "status": "ACTIVE",
                    "exchange": "BINANCE",
                }
            )
        return out

    def fetch_klines_1w(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Fetch 1w klines for [start, end] (inclusive) and return normalized DataFrame.

        Week boundary: Binance 1w open_time is expected to be UTC Monday 00:00:00.
        (Confirmed by live probe: scripts/tests/test_crypto_binance_klines_1w_live.py)

        Returns columns:
          symbol, week_start, week_end, open, high, low, close, volume_quote, exchange, source

        Notes:
        - week_start uses UTC date at kline open time.
        - week_end is computed as week_start + 6 days (UTC Monday..Sunday).
        - volume_quote uses quoteAssetVolume.
        """
        start_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(
            datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000
        )

        all_rows: list[list[Any]] = []
        limit = 1000
        cur_start = start_ms

        while True:
            self._limiter.acquire()
            url = f"{self.cfg.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1w",
                "startTime": cur_start,
                "endTime": end_ms,
                "limit": limit,
            }
            r = requests.get(url, params=params, timeout=self.cfg.timeout_sec)
            r.raise_for_status()
            batch = r.json() or []
            if not batch:
                break

            all_rows.extend(batch)
            last_open_time = int(batch[-1][0])
            next_start = last_open_time + 1
            if next_start > end_ms:
                break
            if len(batch) < limit:
                break
            cur_start = next_start

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            all_rows,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume_base",
                "close_time",
                "quote_asset_volume",
                "num_trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        dt = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["week_start"] = dt.dt.date
        # week_end: week_start + 6 days (Mon..Sun)
        from datetime import timedelta as _td

        df["week_end"] = df["week_start"].apply(lambda d: d + _td(days=6))

        for c in ["open", "high", "low", "close", "quote_asset_volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        out = pd.DataFrame(
            {
                "symbol": symbol,
                "week_start": df["week_start"],
                "week_end": df["week_end"],
                "open": df["open"],
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "volume_quote": df["quote_asset_volume"],
                "exchange": "BINANCE",
                "source": "binance",
            }
        )

        # defensive filter
        out = out[(out["week_start"] >= start) & (out["week_start"] <= end)].copy()
        return out

    def fetch_klines_1d(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Fetch 1d klines for [start, end] (inclusive) and return normalized DataFrame.

        Returns columns:
          symbol, date, open, high, low, close, volume_quote, exchange, source

        Notes:
        - Binance klines uses milliseconds timestamps.
        - date uses UTC date at kline open time.
        - volume_quote uses quoteAssetVolume.
        """
        # Binance expects milliseconds
        start_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
        # inclusive end: set to end 23:59:59
        end_ms = int(
            datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000
        )

        all_rows: list[list[Any]] = []
        limit = 1000
        cur_start = start_ms

        while True:
            self._limiter.acquire()
            url = f"{self.cfg.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1d",
                "startTime": cur_start,
                "endTime": end_ms,
                "limit": limit,
            }
            r = requests.get(url, params=params, timeout=self.cfg.timeout_sec)
            r.raise_for_status()
            batch = r.json() or []
            if not batch:
                break

            all_rows.extend(batch)
            # next page: open time of last candle + 1ms
            last_open_time = int(batch[-1][0])
            next_start = last_open_time + 1
            if next_start > end_ms:
                break
            if len(batch) < limit:
                break
            cur_start = next_start

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            all_rows,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume_base",
                "close_time",
                "quote_asset_volume",
                "num_trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        # open_time(ms) -> UTC date
        dt = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["date"] = dt.dt.date

        # numeric conversion
        for c in ["open", "high", "low", "close", "quote_asset_volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        out = pd.DataFrame(
            {
                "symbol": symbol,
                "date": df["date"],
                "open": df["open"],
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "volume_quote": df["quote_asset_volume"],
                "exchange": "BINANCE",
                "source": "binance",
            }
        )

        # filter inclusive range (defensive)
        out = out[(out["date"] >= start) & (out["date"] <= end)].copy()
        return out
