#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probe CLSM source price data without writing to DB.

This script intentionally reuses the same USStockCollector path used by
us_daily_update.py and us_bulk_update.py, then prints the raw FDR response
beside the normalized collector output and existing DB rows.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from collectors.us_stock import USStockCollector
from core.config_loader import load_settings, resolve_source_strategy
from core.db_manager import DBConfig, DBManager


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Probe US source price data for one symbol")
    parser.add_argument("--symbol", default="CLSM")
    parser.add_argument("--market", default="ETF")
    parser.add_argument("--start", default="2025-10-20")
    parser.add_argument("--end", default="2025-10-31")
    parser.add_argument("--source-strategy", default=None, choices=["fdr", "yfinance", "fdr_then_yfinance"])
    return parser.parse_args(argv)


def print_frame(title: str, df: pd.DataFrame) -> None:
    print("")
    print(f"## {title}")
    if df is None or df.empty:
        print("(empty)")
        return
    print(df.to_string(index=False))


def pct_change(prev, curr) -> float | None:
    if prev in (None, 0) or curr is None:
        return None
    return (float(curr) / float(prev) - 1.0) * 100.0


def print_close_gap(title: str, df: pd.DataFrame, close_col: str = "close") -> None:
    if df is None or df.empty or close_col not in df.columns:
        return
    working = df.copy()
    date_col = "date" if "date" in working.columns else working.columns[0]
    working[date_col] = pd.to_datetime(working[date_col])
    working = working.sort_values(date_col)
    print("")
    print(f"## {title} close-to-close gaps")
    prev_row = None
    for _, row in working.iterrows():
        if prev_row is not None:
            gap = pct_change(prev_row[close_col], row[close_col])
            gap_text = "-" if gap is None else f"{gap:.2f}%"
            print(
                f"{prev_row[date_col].date()} -> {row[date_col].date()}: "
                f"{prev_row[close_col]} -> {row[close_col]} ({gap_text})"
            )
        prev_row = row


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))
    source_strategy = args.source_strategy or resolve_source_strategy(cfg, None, "us_stock")

    print(f"symbol={args.symbol} market={args.market} range={args.start}..{args.end}")
    print(f"collector_source_strategy={source_strategy}")

    import FinanceDataReader as fdr

    df_fdr_raw = fdr.DataReader(args.symbol, start=args.start, end=args.end)
    raw_for_print = df_fdr_raw.reset_index()
    print_frame("FinanceDataReader raw DataReader()", raw_for_print)

    collector = USStockCollector(engine, source_strategy=source_strategy)
    df_collector = collector.fetch(args.symbol, start=args.start, end=args.end, market=args.market)
    print_frame(f"USStockCollector.fetch() normalized source={collector.last_fetch_source}", df_collector)
    print_close_gap("collector", df_collector, "close")

    with engine.connect() as conn:
        db_rows = conn.execute(
            text(
                """
                SELECT symbol, date, open, high, low, close, adj_close, volume, market, source
                FROM us_stock_prices
                WHERE symbol = :symbol
                  AND date BETWEEN :start AND :end
                ORDER BY date
                """
            ),
            {"symbol": args.symbol, "start": args.start, "end": args.end},
        ).mappings().all()

    df_db = pd.DataFrame([dict(row) for row in db_rows])
    print_frame("Existing DB us_stock_prices", df_db)
    print_close_gap("db", df_db, "close")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
