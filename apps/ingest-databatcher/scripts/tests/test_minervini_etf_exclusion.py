#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADR-013 ETF 제외 로직 단위 테스트

미너비니 스크리너(us_minervini_update, kr_minervini_update)에서
ETF가 스크리닝 결과에 포함되지 않음을 검증.
"""
from __future__ import annotations

import unittest
import pandas as pd


# ── ADR-013 필터 로직 (두 스크립트 공통 패턴을 함수로 추출해 테스트) ────────────

def apply_etf_filter(symbol_details: list[dict]) -> tuple[list[dict], set[str], int]:
    """
    symbol_details에서 symbol_type='ETF'인 항목 제거.

    Returns:
        (filtered_details, non_etf_symbols, etf_excluded_count)
    """
    total_before = len(symbol_details)
    filtered = [d for d in symbol_details if d.get("symbol_type") != "ETF"]
    excluded = total_before - len(filtered)
    non_etf = {d["symbol"] for d in filtered}
    return filtered, non_etf, excluded


def filter_prices_wide(prices_wide: pd.DataFrame, non_etf_symbols: set[str]) -> pd.DataFrame:
    """prices_wide에서 non_etf_symbols에 없는 컬럼(ETF) 제거."""
    etf_cols = [c for c in prices_wide.columns if c not in non_etf_symbols]
    if etf_cols:
        return prices_wide.drop(columns=etf_cols)
    return prices_wide


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

class TestEtfFilterSymbolDetails(unittest.TestCase):

    def _make_details(self, rows):
        return [{"symbol": s, "name": n, "market": m, "symbol_type": t}
                for s, n, m, t in rows]

    def test_etf_excluded_us(self):
        details = self._make_details([
            ("AAPL", "Apple", "NASDAQ", "STOCK"),
            ("MSFT", "Microsoft", "NYSE", "STOCK"),
            ("SPY",  "SPDR S&P 500", "ETF", "ETF"),
            ("QQQ",  "Invesco QQQ", "ETF", "ETF"),
        ])
        filtered, non_etf, excluded = apply_etf_filter(details)
        self.assertEqual(excluded, 2)
        self.assertEqual(len(filtered), 2)
        self.assertNotIn("SPY", non_etf)
        self.assertNotIn("QQQ", non_etf)
        self.assertIn("AAPL", non_etf)
        self.assertIn("MSFT", non_etf)

    def test_etf_excluded_kr(self):
        details = self._make_details([
            ("005930", "삼성전자", "KOSPI", "STOCK"),
            ("000660", "SK하이닉스", "KOSPI", "STOCK"),
            ("069500", "KODEX 200", "ETF", "ETF"),
            ("122630", "KODEX 레버리지", "ETF", "ETF"),
        ])
        filtered, non_etf, excluded = apply_etf_filter(details)
        self.assertEqual(excluded, 2)
        self.assertEqual(len(filtered), 2)
        self.assertNotIn("069500", non_etf)
        self.assertNotIn("122630", non_etf)
        self.assertIn("005930", non_etf)

    def test_all_stocks_unchanged(self):
        details = self._make_details([
            ("AAPL", "Apple", "NASDAQ", "STOCK"),
            ("TSLA", "Tesla", "NASDAQ", "STOCK"),
        ])
        filtered, non_etf, excluded = apply_etf_filter(details)
        self.assertEqual(excluded, 0)
        self.assertEqual(len(filtered), 2)

    def test_symbol_type_none_treated_as_stock(self):
        """symbol_type=NULL인 종목은 STOCK으로 간주해 제외 안 함."""
        details = [
            {"symbol": "XYZ", "name": "XYZ Corp", "market": "NYSE", "symbol_type": None},
        ]
        filtered, non_etf, excluded = apply_etf_filter(details)
        self.assertEqual(excluded, 0)
        self.assertIn("XYZ", non_etf)

    def test_empty_list(self):
        filtered, non_etf, excluded = apply_etf_filter([])
        self.assertEqual(filtered, [])
        self.assertEqual(non_etf, set())
        self.assertEqual(excluded, 0)

    def test_all_etf_returns_empty(self):
        details = self._make_details([
            ("SPY", "SPY", "ETF", "ETF"),
            ("QQQ", "QQQ", "ETF", "ETF"),
        ])
        filtered, non_etf, excluded = apply_etf_filter(details)
        self.assertEqual(len(filtered), 0)
        self.assertEqual(len(non_etf), 0)
        self.assertEqual(excluded, 2)


class TestEtfFilterPricesWide(unittest.TestCase):

    def _make_prices(self, symbols: list[str]) -> pd.DataFrame:
        dates = pd.date_range("2026-01-01", periods=5, freq="B")
        return pd.DataFrame(1.0, index=dates, columns=symbols)

    def test_etf_columns_removed(self):
        prices = self._make_prices(["AAPL", "MSFT", "SPY", "QQQ"])
        non_etf = {"AAPL", "MSFT"}
        result = filter_prices_wide(prices, non_etf)
        self.assertListEqual(sorted(result.columns.tolist()), ["AAPL", "MSFT"])

    def test_no_etf_columns_unchanged(self):
        prices = self._make_prices(["AAPL", "MSFT"])
        non_etf = {"AAPL", "MSFT"}
        result = filter_prices_wide(prices, non_etf)
        self.assertListEqual(sorted(result.columns.tolist()), ["AAPL", "MSFT"])

    def test_screener_result_contains_no_etf(self):
        """prices_wide에서 ETF 제거 후 screener 결과에 ETF 없음을 end-to-end 검증."""
        prices = self._make_prices(["AAPL", "MSFT", "SPY", "QQQ"])
        # SPY, QQQ 는 ETF → non_etf_symbols에서 제외됨
        non_etf = {"AAPL", "MSFT"}
        filtered_prices = filter_prices_wide(prices, non_etf)

        # 어떤 pass_mask를 만들어도 ETF 컬럼이 없으므로 결과에 ETF 없음
        pass_mask = filtered_prices > 0  # 모두 통과
        melted = pass_mask.reset_index().melt(id_vars=["index"], var_name="symbol", value_name="pass")
        melted = melted[melted["pass"]]
        self.assertNotIn("SPY", melted["symbol"].values)
        self.assertNotIn("QQQ", melted["symbol"].values)
        self.assertIn("AAPL", melted["symbol"].values)
        self.assertIn("MSFT", melted["symbol"].values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
