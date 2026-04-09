#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from sqlalchemy import create_engine

from collectors.us_stock import USStockCollector


def test_us_stock_collector_fetch_fdr_normalizes_columns(monkeypatch):
    sample = pd.DataFrame(
        {
            "Open": [10.0],
            "High": [11.0],
            "Low": [9.0],
            "Close": [10.5],
            "Adj Close": [10.4],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2025-12-01"]),
    )

    fake_fdr = SimpleNamespace(DataReader=lambda symbol, start, end: sample)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)

    collector = USStockCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr")
    df = collector.fetch("AAPL", "2025-12-01", "2025-12-10", market="NASDAQ")

    assert list(df.columns) == [
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
    assert df.iloc[0]["symbol"] == "AAPL"
    assert df.iloc[0]["market"] == "NASDAQ"
    assert df.iloc[0]["source"] == "fdr"
    assert df.iloc[0]["adj_close"] == 10.4
    assert collector.last_fetch_source == "fdr"


def test_us_stock_collector_clips_rows_outside_requested_range(monkeypatch):
    sample = pd.DataFrame(
        {
            "Open": [9.0, 10.0],
            "High": [10.0, 11.0],
            "Low": [8.0, 9.0],
            "Close": [9.5, 10.5],
            "Adj Close": [9.4, 10.4],
            "Volume": [900, 1000],
        },
        index=pd.to_datetime(["2025-11-30", "2025-12-01"]),
    )

    fake_fdr = SimpleNamespace(DataReader=lambda symbol, start, end: sample)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)

    collector = USStockCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr")
    df = collector.fetch("AAPL", "2025-12-01", "2025-12-10", market="NASDAQ")

    assert len(df) == 1
    assert str(df.iloc[0]["date"]) == "2025-12-01"


def test_us_stock_collector_fetch_yfinance_flattens_multiindex(monkeypatch):
    columns = pd.MultiIndex.from_tuples(
        [
            ("Adj Close", "BRK-B"),
            ("Close", "BRK-B"),
            ("High", "BRK-B"),
            ("Low", "BRK-B"),
            ("Open", "BRK-B"),
            ("Volume", "BRK-B"),
        ]
    )
    sample = pd.DataFrame(
        [[500.1, 500.2, 501.0, 499.0, 500.0, 12345]],
        index=pd.to_datetime(["2025-12-01"]),
        columns=columns,
    )

    fake_yf = SimpleNamespace(download=lambda symbol, start, end, auto_adjust, progress: sample)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    collector = USStockCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="yfinance")
    df = collector.fetch("BRK-B", "2025-12-01", "2025-12-10", market="NYSE")

    assert df.iloc[0]["symbol"] == "BRK-B"
    assert df.iloc[0]["market"] == "NYSE"
    assert df.iloc[0]["source"] == "yfinance"
    assert df.iloc[0]["open"] == 500.0
    assert df.iloc[0]["adj_close"] == 500.1
    assert collector.last_fetch_source == "yfinance"


def test_us_stock_collector_fallback_uses_yfinance_after_fdr_error(monkeypatch):
    def _raise_fdr(symbol, start, end):
        raise RuntimeError("fdr down")

    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "AAPL"),
            ("High", "AAPL"),
            ("Low", "AAPL"),
            ("Open", "AAPL"),
            ("Volume", "AAPL"),
        ]
    )
    sample_yf = pd.DataFrame(
        [[300.0, 301.0, 299.0, 299.5, 2000]],
        index=pd.to_datetime(["2025-12-01"]),
        columns=columns,
    )

    fake_fdr = SimpleNamespace(DataReader=_raise_fdr)
    fake_yf = SimpleNamespace(download=lambda symbol, start, end, auto_adjust, progress: sample_yf)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    collector = USStockCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr_then_yfinance")
    df = collector.fetch("AAPL", "2025-12-01", "2025-12-10", market="NASDAQ")

    assert df.iloc[0]["source"] == "yfinance"
    assert df.iloc[0]["adj_close"] == df.iloc[0]["close"]
    assert collector.last_fetch_source == "yfinance"
    assert collector.last_fetch_note == "fdr failed: fdr down"
