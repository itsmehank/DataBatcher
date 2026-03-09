#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 주식(ETF 포함) IBD RS Rating + RS Line + Blue Dot 일괄 계산/저장

전 종목 횡단면(cross-sectional) 기반 지표이므로 기존 per-symbol 파이프라인이 아닌
별도 배치 스크립트로 구현. 저장은 기존 stock_indicators 테이블(long-form)을 재사용한다.

처리 흐름:
  1. symbol_master에서 ACTIVE 종목 목록 로드
  2. stock_prices에서 전 종목 close 가격 로드 (wide format, ~252+days)
  3. kr_index_prices에서 KOSPI(1001) close 로드
  4. IBD RS Rating 계산 (전 종목 횡단면)
  5. RS Line 계산 (각 종목 vs KOSPI)
  6. Blue Dot 계산 (RS Line + 주가 기반)
  7. 최근 N일에 대해 long-form 변환 → stock_indicators에 INSERT ONLY 저장

실행 예:
    python scripts/kr_rs_update.py
    python scripts/kr_rs_update.py --days 5
    python scripts/kr_rs_update.py --market KOSPI --days 30
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.date_utils import DateUtils
from core.params import params_hash
from core.bulk_price_loader import load_all_prices_wide, load_index_close
from core.symbol_loader import load_symbols_from_master
from savers.indicator_saver import IndicatorSaver
from indicators.ibd.rs_rating import calculate_ibd_rs_rating
from indicators.ibd.rs_line import calculate_rs_line_bulk
from indicators.ibd.blue_dot import calculate_blue_dot_bulk

# warmup: RS Rating은 12개월(252일) 수익률이 필요
# 252 거래일은 약 365 캘린더일에 해당. timedelta(days=)에서 사용하므로 여유분 포함
WARMUP_DAYS = 400


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="KR 주식 IBD RS Rating / RS Line / Blue Dot 배치")
    p.add_argument("--end", default=None,
                   help="기준 종료일 (YYYY-MM-DD). 미지정 시 마지막 마감 완료 영업일")
    p.add_argument("--days", type=int, default=30,
                   help="저장 대상 일수 (기본: 30, 최근 N 거래일)")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "ETF", "ALL"],
                   default="ALL", help="대상 마켓 (기본: ALL)")
    p.add_argument("--strict-12m", dest="strict_12m", action="store_true", default=None,
                   help="12개월 미만 종목 제외 (기본: config 값)")
    p.add_argument("--no-strict-12m", dest="strict_12m", action="store_false",
                   help="12개월 미만 종목 포함")
    return p.parse_args(argv)


def to_long_form(
    df_wide: pd.DataFrame,
    indicator: str,
    p_hash: str,
    source: str,
    symbol_market_map: dict[str, str],
    save_dates: list,
) -> pd.DataFrame:
    """wide-format DataFrame을 long-form(stock_indicators 형식)으로 변환."""
    # save_dates에 해당하는 행만 추출
    save_idx = pd.DatetimeIndex([pd.Timestamp(d) for d in save_dates])
    available = df_wide.index.intersection(save_idx)
    if available.empty:
        return pd.DataFrame()

    subset = df_wide.loc[available]
    subset.index.name = "date"  # 연산 과정에서 index name 유실 방지

    # melt: wide → long
    melted = subset.reset_index().melt(
        id_vars=["date"],
        var_name="symbol",
        value_name="value",
    )

    # NaN 행 제거
    melted = melted.dropna(subset=["value"])

    if melted.empty:
        return pd.DataFrame()

    melted["indicator"] = indicator
    melted["params_hash"] = p_hash
    melted["source"] = source
    melted["market"] = melted["symbol"].map(symbol_market_map).fillna("KOSPI")
    melted["date"] = pd.to_datetime(melted["date"]).dt.date

    return melted[["symbol", "date", "indicator", "params_hash", "value", "market", "source"]]


def main(argv=None) -> int:
    args = parse_args(argv)

    cfg = load_settings()
    db_cfg = DBConfig(**cfg["database"])
    engine = DBManager.get_engine(db_cfg)

    # IBD RS 설정 로드
    ibd_cfg = cfg.get("ibd_rs", {})
    strict_12m = args.strict_12m if args.strict_12m is not None else ibd_cfg.get("strict_12m", True)
    rs_weights = ibd_cfg.get("rs_rating_weights", {"3m": 0.4, "6m": 0.2, "9m": 0.2, "12m": 0.2})
    blue_dot_lookback = ibd_cfg.get("blue_dot_lookback", 252)
    benchmark_symbol = ibd_cfg.get("benchmarks", {}).get("kr", "1001")

    # 종료일(마감 완료 영업일) 계산
    du = DateUtils(cfg.get("runtime", {}).get("timezone", "Asia/Seoul"))
    mk_close = cfg.get("markets", {}).get("close_times", {}).get("XKRX", "16:00")
    buffer_min = int(cfg.get("markets", {}).get("safe_delay_minutes", 30))
    last_biz = du.get_last_closed_business_day("XKRX", mk_close, buffer_min)
    end_d: date = pd.to_datetime(args.end).date() if args.end else last_biz

    # DB 로드 범위: warmup + days
    load_start = end_d - timedelta(days=WARMUP_DAYS + args.days + 60)  # 여유분

    print(f"[kr_rs_update] market={args.market} end={end_d} days={args.days} strict_12m={strict_12m}")
    print(f"[kr_rs_update] benchmark={benchmark_symbol} load_start={load_start}")

    # 1. 종목 목록 로드 (symbol → market 매핑용)
    from core.symbol_loader import load_symbols_with_details
    symbol_details = load_symbols_with_details(engine, market=args.market)
    if not symbol_details:
        print("Error: ACTIVE 종목 없음. sync_symbol_master.py 먼저 실행", file=sys.stderr)
        return 2

    symbol_market_map = {d["symbol"]: d["market"] for d in symbol_details}
    print(f"[kr_rs_update] 종목 수: {len(symbol_details)}")

    # 2. 전 종목 close 가격 로드 (wide format)
    prices_wide = load_all_prices_wide(
        engine, load_start, end_d,
        table="stock_prices",
        market=args.market if args.market != "ALL" else None,
    )
    if prices_wide.empty:
        print("Error: 가격 데이터 없음", file=sys.stderr)
        return 2

    print(f"[kr_rs_update] 가격 로드: {prices_wide.shape[0]}일 x {prices_wide.shape[1]}종목")

    # 3. 벤치마크 지수 close 로드
    index_close = load_index_close(
        engine, benchmark_symbol, load_start, end_d,
        table="kr_index_prices",
    )
    if index_close.empty:
        print(f"Error: 벤치마크 지수({benchmark_symbol}) 데이터 없음", file=sys.stderr)
        return 2

    print(f"[kr_rs_update] 지수 로드: {len(index_close)}일 ({benchmark_symbol})")

    # 4. IBD RS Rating 계산
    print("[kr_rs_update] IBD RS Rating 계산 중...")
    rs_rating = calculate_ibd_rs_rating(prices_wide, weights=rs_weights, strict_12m=strict_12m)

    # 5. RS Line 계산
    print("[kr_rs_update] RS Line 계산 중...")
    rs_line = calculate_rs_line_bulk(prices_wide, index_close)

    # 6. Blue Dot 계산
    print("[kr_rs_update] Blue Dot 계산 중...")
    blue_dot = calculate_blue_dot_bulk(prices_wide, rs_line, lookback=blue_dot_lookback)

    # 7. 저장 대상 날짜 결정 (최근 N 거래일)
    all_dates = sorted(prices_wide.index)
    save_dates = all_dates[-args.days:] if len(all_dates) >= args.days else all_dates
    print(f"[kr_rs_update] 저장 대상: {len(save_dates)}일 ({save_dates[0].date()} ~ {save_dates[-1].date()})")

    # params_hash 계산
    hash_rs_rating = params_hash("ibd_rs_rating", {"strict_12m": strict_12m})
    hash_rs_line = params_hash("rs_line", {"benchmark": benchmark_symbol})
    hash_blue_dot = params_hash("blue_dot", {"lookback": blue_dot_lookback, "benchmark": benchmark_symbol})

    # long-form 변환
    source = "pykrx"

    df_rs_rating = to_long_form(rs_rating, "ibd_rs_rating", hash_rs_rating, source, symbol_market_map, save_dates)
    df_rs_line = to_long_form(rs_line, "rs_line", hash_rs_line, source, symbol_market_map, save_dates)
    df_blue_dot = to_long_form(blue_dot, "blue_dot", hash_blue_dot, source, symbol_market_map, save_dates)

    # 저장
    table_long = cfg.get("indicators", {}).get("materialization", {}).get("table_long", "stock_indicators")
    saver = IndicatorSaver(engine, table_long=table_long)

    total = 0
    for label, df_long in [("ibd_rs_rating", df_rs_rating), ("rs_line", df_rs_line), ("blue_dot", df_blue_dot)]:
        if df_long is not None and not df_long.empty:
            rows = saver.save_long(df_long, mode="insert_only")
            print(f"[kr_rs_update] {label}: {rows}건 저장")
            total += rows
        else:
            print(f"[kr_rs_update] {label}: 저장할 데이터 없음")

    print(f"[kr_rs_update] 완료. 총 {total}건 저장")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
