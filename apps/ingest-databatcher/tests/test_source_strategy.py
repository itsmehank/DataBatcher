#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import resolve_indicator_source, resolve_source_strategy


def test_resolve_source_strategy_uses_cli_override():
    cfg = {"collectors": {"us_stock": {"source_strategy": "fdr"}}}
    assert resolve_source_strategy(cfg, "yfinance", "us_stock") == "yfinance"


def test_resolve_source_strategy_uses_config_default():
    cfg = {"collectors": {"us_index": {"source_strategy": "fdr_then_yfinance"}}}
    assert resolve_source_strategy(cfg, None, "us_index") == "fdr_then_yfinance"


def test_resolve_source_strategy_rejects_invalid_value():
    cfg = {"collectors": {"us_stock": {"source_strategy": "invalid"}}}
    with pytest.raises(ValueError, match="Unsupported source_strategy"):
        resolve_source_strategy(cfg, None, "us_stock")


def test_resolve_indicator_source_prefers_last_fetch_source():
    collector = SimpleNamespace(last_fetch_source="yfinance", source_strategy="fdr_then_yfinance")
    assert resolve_indicator_source(collector) == "yfinance"


def test_resolve_indicator_source_falls_back_to_strategy():
    collector = SimpleNamespace(last_fetch_source=None, source_strategy="fdr")
    assert resolve_indicator_source(collector) == "fdr"
