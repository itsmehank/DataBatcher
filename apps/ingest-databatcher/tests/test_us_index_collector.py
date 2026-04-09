#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.us_index import USIndexCollector


def test_us_index_collector_fetch_fdr_normalizes_columns(monkeypatch):
    sample = pd.DataFrame(
        {
            "Open": [6000.0],
            "High": [6020.0],
            "Low": [5980.0],
            "Close": [6010.0],
            "Volume": [1000000],
            "Adj Close": [6010.0],
        },
        index=pd.to_datetime(["2025-12-01"]),
    )

    fake_fdr = SimpleNamespace(DataReader=lambda symbol, start, end: sample)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)

    collector = USIndexCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr")
    df = collector.fetch("US500", "2025-12-01", "2025-12-10", market="SP500")

    assert list(df.columns) == [
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
    assert df.iloc[0]["symbol"] == "US500"
    assert df.iloc[0]["market"] == "SP500"
    assert df.iloc[0]["source"] == "fdr"
    assert collector.last_fetch_source == "fdr"


def test_us_index_collector_clips_rows_outside_requested_range(monkeypatch):
    sample = pd.DataFrame(
        {
            "Open": [5990.0, 6000.0],
            "High": [6010.0, 6020.0],
            "Low": [5970.0, 5980.0],
            "Close": [6000.0, 6010.0],
            "Volume": [900000, 1000000],
        },
        index=pd.to_datetime(["2025-11-30", "2025-12-01"]),
    )

    fake_fdr = SimpleNamespace(DataReader=lambda symbol, start, end: sample)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)

    collector = USIndexCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr")
    df = collector.fetch("US500", "2025-12-01", "2025-12-10", market="SP500")

    assert len(df) == 1
    assert str(df.iloc[0]["date"]) == "2025-12-01"


def test_us_index_collector_fetch_yfinance_maps_symbol(monkeypatch):
    captured = {}

    def _download(symbol, start, end, auto_adjust, progress):
        captured["symbol"] = symbol
        columns = pd.MultiIndex.from_tuples(
            [
                ("Adj Close", symbol),
                ("Close", symbol),
                ("High", symbol),
                ("Low", symbol),
                ("Open", symbol),
                ("Volume", symbol),
            ]
        )
        return pd.DataFrame(
            [[6010.0, 6010.0, 6020.0, 5980.0, 6000.0, 1000000]],
            index=pd.to_datetime(["2025-12-01"]),
            columns=columns,
        )

    fake_yf = SimpleNamespace(download=_download)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    collector = USIndexCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="yfinance")
    df = collector.fetch("US500", "2025-12-01", "2025-12-10", market="SP500")

    assert captured["symbol"] == "^GSPC"
    assert df.iloc[0]["symbol"] == "US500"
    assert df.iloc[0]["source"] == "yfinance"
    assert df.iloc[0]["close"] == 6010.0
    assert collector.last_fetch_source == "yfinance"


def test_us_index_collector_fallback_uses_yfinance_after_fdr_error(monkeypatch):
    def _raise_fdr(symbol, start, end):
        raise RuntimeError("fdr down")

    def _download(symbol, start, end, auto_adjust, progress):
        columns = pd.MultiIndex.from_tuples(
            [
                ("Close", symbol),
                ("High", symbol),
                ("Low", symbol),
                ("Open", symbol),
                ("Volume", symbol),
            ]
        )
        return pd.DataFrame(
            [[6010.0, 6020.0, 5980.0, 6000.0, 1000000]],
            index=pd.to_datetime(["2025-12-01"]),
            columns=columns,
        )

    fake_fdr = SimpleNamespace(DataReader=_raise_fdr)
    fake_yf = SimpleNamespace(download=_download)
    monkeypatch.setitem(sys.modules, "FinanceDataReader", fake_fdr)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    collector = USIndexCollector(engine=create_engine("sqlite:///:memory:"), source_strategy="fdr_then_yfinance")
    df = collector.fetch("IXIC", "2025-12-01", "2025-12-10", market="IXIC")

    assert df.iloc[0]["source"] == "yfinance"
    assert collector.last_fetch_source == "yfinance"
    assert collector.last_fetch_note == "fdr failed: fdr down"
