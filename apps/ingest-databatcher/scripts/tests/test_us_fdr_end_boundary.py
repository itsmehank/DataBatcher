"""
FDR `end` 경계 보정 회귀 테스트.

FDR.DataReader는 `end`를 exclusive(`< end`)로 처리하므로,
collector는 logical_end + 1 day를 FDR에 전달하고
응답에서 logical_end를 초과하는 행은 잘라내야 한다.

이 테스트는 fdr.DataReader / yfinance.download를 mock으로 가로채
collector 동작을 검증한다 (DB / 네트워크 무관).
"""
from __future__ import annotations

import datetime as dt
import sys
import types
from unittest import mock

import pandas as pd
import pytest

from collectors.us_index import USIndexCollector
from collectors.us_stock import USStockCollector


def _fdr_response(dates: list[str], with_adj_close: bool = True) -> pd.DataFrame:
    """Build a mock FDR-style DataFrame indexed by Date with OHLCV columns."""
    idx = pd.to_datetime(dates)
    base = {
        "Open": [100.0 + i for i in range(len(dates))],
        "High": [110.0 + i for i in range(len(dates))],
        "Low": [90.0 + i for i in range(len(dates))],
        "Close": [105.0 + i for i in range(len(dates))],
        "Volume": [1000 + i for i in range(len(dates))],
    }
    if with_adj_close:
        base["Adj Close"] = base["Close"]
    df = pd.DataFrame(base, index=idx)
    df.index.name = "Date"
    return df


def _install_fake_fdr(captured: dict, response: pd.DataFrame) -> None:
    """Inject a fake FinanceDataReader module so collector imports it."""
    fake = types.ModuleType("FinanceDataReader")

    def _DataReader(symbol, start, end):
        captured["symbol"] = symbol
        captured["start"] = start
        captured["end"] = end
        return response.copy()

    fake.DataReader = _DataReader
    sys.modules["FinanceDataReader"] = fake


# ---------------------------------------------------------------------------
# us_stock.py
# ---------------------------------------------------------------------------

def test_us_stock_passes_end_plus_one_to_fdr():
    captured: dict = {}
    _install_fake_fdr(captured, _fdr_response(["2026-05-05", "2026-05-06"]))

    collector = USStockCollector(engine=mock.MagicMock(), source_strategy="fdr")
    collector.fetch("AAPL", start="2026-05-05", end="2026-05-06", market="NASDAQ")

    assert captured["start"] == "2026-05-05"
    assert captured["end"] == "2026-05-07", (
        f"FDR must receive logical_end + 1 day, got end={captured['end']!r}"
    )


def test_us_stock_trims_future_dates_returned_by_fdr():
    """Even if FDR returns a row dated > logical_end, collector must drop it."""
    response = _fdr_response(["2026-05-05", "2026-05-06", "2026-05-07"])
    _install_fake_fdr({}, response)

    collector = USStockCollector(engine=mock.MagicMock(), source_strategy="fdr")
    df = collector.fetch("AAPL", start="2026-05-05", end="2026-05-06", market="NASDAQ")

    dates = sorted(d.isoformat() for d in df["date"].tolist())
    assert dates == ["2026-05-05", "2026-05-06"], dates


def test_us_stock_keeps_logical_end_row():
    response = _fdr_response(["2026-05-05", "2026-05-06"])
    _install_fake_fdr({}, response)

    collector = USStockCollector(engine=mock.MagicMock(), source_strategy="fdr")
    df = collector.fetch("AAPL", start="2026-05-05", end="2026-05-06", market="NASDAQ")

    dates = sorted(d.isoformat() for d in df["date"].tolist())
    assert "2026-05-06" in dates, f"logical_end row missing: {dates}"


def test_us_stock_accepts_date_objects():
    captured: dict = {}
    _install_fake_fdr(captured, _fdr_response(["2026-05-05", "2026-05-06"]))

    collector = USStockCollector(engine=mock.MagicMock(), source_strategy="fdr")
    collector.fetch(
        "AAPL",
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 6),
        market="NASDAQ",
    )

    # FDR call still receives string-formatted end+1
    assert captured["end"] == "2026-05-07"


# ---------------------------------------------------------------------------
# us_index.py
# ---------------------------------------------------------------------------

def test_us_index_passes_end_plus_one_to_fdr():
    captured: dict = {}
    _install_fake_fdr(
        captured,
        _fdr_response(["2026-05-05", "2026-05-06"], with_adj_close=False),
    )

    collector = USIndexCollector(engine=mock.MagicMock(), source_strategy="fdr")
    collector.fetch("US500", start="2026-05-05", end="2026-05-06", market="SP500")

    assert captured["start"] == "2026-05-05"
    assert captured["end"] == "2026-05-07", (
        f"FDR must receive logical_end + 1 day, got end={captured['end']!r}"
    )


def test_us_index_trims_future_dates_returned_by_fdr():
    response = _fdr_response(
        ["2026-05-05", "2026-05-06", "2026-05-07"], with_adj_close=False
    )
    _install_fake_fdr({}, response)

    collector = USIndexCollector(engine=mock.MagicMock(), source_strategy="fdr")
    df = collector.fetch("US500", start="2026-05-05", end="2026-05-06", market="SP500")

    dates = sorted(d.isoformat() for d in df["date"].tolist())
    assert dates == ["2026-05-05", "2026-05-06"], dates


def test_us_index_keeps_logical_end_row():
    response = _fdr_response(["2026-05-05", "2026-05-06"], with_adj_close=False)
    _install_fake_fdr({}, response)

    collector = USIndexCollector(engine=mock.MagicMock(), source_strategy="fdr")
    df = collector.fetch("US500", start="2026-05-05", end="2026-05-06", market="SP500")

    dates = sorted(d.isoformat() for d in df["date"].tolist())
    assert "2026-05-06" in dates, f"logical_end row missing: {dates}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
