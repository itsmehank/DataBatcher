#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 주식 미너비니 트렌드 템플릿 스크리닝 배치

처리 흐름:
  1. symbol_master에서 ACTIVE 종목 목록 로드
  2. stock_prices에서 전 종목 close 가격 로드 (wide format, ~252+days+60)
  3. stock_indicators에서 RS Rating, Blue Dot 로드 (이미 계산된 것 재사용)
  4. 미너비니 트렌드 템플릿 스크리닝 수행
  5. 통과 종목만 minervini_screen_results_kr에 INSERT ONLY 저장

실행 예:
    python scripts/kr_minervini_update.py --days 9999  # 전체 백필
    python scripts/kr_minervini_update.py --days 7     # 최근 7일
    python scripts/kr_minervini_update.py --market KOSPI --days 30
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.date_utils import DateUtils
from core.params import params_hash
from core.bulk_price_loader import load_all_prices_wide, load_indicators_wide
from core.symbol_loader import load_symbols_with_details
from indicators.minervini.trend_template import screen_minervini_trend_template

# warmup: 52주(252거래일) + SMA200(200거래일) → 캘린더일로 환산 시 ~400일 필요
# (252 거래일 * 1.45 캘린더/거래일 환산 비율 = 365일, 여유를 위해 400일 설정)
WARMUP_DAYS = 400


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="KR 주식 미너비니 트렌드 템플릿 스크리닝 배치")
    p.add_argument("--end", default=None,
                   help="기준 종료일 (YYYY-MM-DD). 미지정 시 마지막 마감 완료 영업일")
    p.add_argument("--days", type=int, default=30,
                   help="저장 대상 일수 (기본: 30, 최근 N 거래일)")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "ETF", "ALL"],
                   default="ALL", help="대상 마켓 (기본: ALL)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    cfg = load_settings()
    db_cfg = DBConfig(**cfg["database"])
    engine = DBManager.get_engine(db_cfg)

    # 미너비니 설정 로드
    minervini_cfg = cfg.get("minervini_kr", {})
    filters_cfg = minervini_cfg.get("filters", {})

    # 종료일(마감 완료 영업일) 계산
    du = DateUtils(cfg.get("runtime", {}).get("timezone", "Asia/Seoul"))
    mk_close = cfg.get("markets", {}).get("close_times", {}).get("XKRX", "16:00")
    buffer_min = int(cfg.get("markets", {}).get("safe_delay_minutes", 30))
    last_biz = du.get_last_closed_business_day("XKRX", mk_close, buffer_min)
    end_d: date = pd.to_datetime(args.end).date() if args.end else last_biz

    # DB 로드 범위: warmup + days + 60
    load_start = end_d - timedelta(days=WARMUP_DAYS + args.days + 60)

    print(f"[kr_minervini_update] market={args.market} end={end_d} days={args.days}")
    print(f"[kr_minervini_update] load_start={load_start}")

    # 1. 종목 목록 로드 (symbol → market 매핑용)
    symbol_details = load_symbols_with_details(engine, market=args.market)
    if not symbol_details:
        print("Error: ACTIVE 종목 없음. sync_symbol_master.py 먼저 실행", file=sys.stderr)
        return 2

    symbol_market_map = {d["symbol"]: d["market"] for d in symbol_details}
    print(f"[kr_minervini_update] 종목 수: {len(symbol_details)}")

    # 2. 가격 데이터 로드 (wide format)
    prices_wide = load_all_prices_wide(
        engine,
        start_date=load_start,
        end_date=end_d,
        table="stock_prices",
        market=args.market if args.market != "ALL" else None,
    )

    if prices_wide.empty:
        print("Error: 가격 데이터 없음", file=sys.stderr)
        return 3

    print(f"[kr_minervini_update] 가격 데이터: {prices_wide.shape[0]} 거래일 x {prices_wide.shape[1]} 종목")

    # 3. RS Rating, Blue Dot 로드 (선택적)
    rs_rating_wide = None
    blue_dot_wide = None

    if filters_cfg.get("rs_rating", {}).get("enabled", True):
        ibd_cfg = cfg.get("ibd_rs", {})
        strict_12m = ibd_cfg.get("strict_12m", True)
        rs_params = {"strict_12m": strict_12m}
        rs_hash = params_hash("ibd_rs_rating", rs_params)

        rs_rating_wide = load_indicators_wide(
            engine,
            indicator="ibd_rs_rating",
            params_hash_val=rs_hash,
            start_date=load_start,
            end_date=end_d,
            table="stock_indicators",
            market=args.market if args.market != "ALL" else None,
        )

        if rs_rating_wide.empty:
            print(
                "Error: rs_rating 필터가 enabled=true인데 RS Rating 데이터가 없습니다. "
                "kr_rs_update.py를 먼저 실행하세요.",
                file=sys.stderr,
            )
            return 5
        else:
            print(f"[kr_minervini_update] RS Rating: {rs_rating_wide.shape[0]} 거래일 x {rs_rating_wide.shape[1]} 종목")

    if filters_cfg.get("blue_dot", {}).get("enabled", False):
        ibd_cfg = cfg.get("ibd_rs", {})
        benchmark_symbol = ibd_cfg.get("benchmarks", {}).get("kr", "1001")
        blue_dot_lookback = ibd_cfg.get("blue_dot_lookback", 252)
        bd_params = {"benchmark": benchmark_symbol, "lookback": blue_dot_lookback}
        bd_hash = params_hash("blue_dot", bd_params)

        blue_dot_wide = load_indicators_wide(
            engine,
            indicator="blue_dot",
            params_hash_val=bd_hash,
            start_date=load_start,
            end_date=end_d,
            table="stock_indicators",
            market=args.market if args.market != "ALL" else None,
        )

        if blue_dot_wide.empty:
            print(
                "Error: blue_dot 필터가 enabled=true인데 Blue Dot 데이터가 없습니다. "
                "kr_rs_update.py를 먼저 실행하세요.",
                file=sys.stderr,
            )
            return 6
        else:
            print(f"[kr_minervini_update] Blue Dot: {blue_dot_wide.shape[0]} 거래일 x {blue_dot_wide.shape[1]} 종목")

    # 4. 미너비니 스크리닝 실행
    print("[kr_minervini_update] 미너비니 트렌드 템플릿 스크리닝 실행...")
    pass_mask, _, conditions = screen_minervini_trend_template(
        prices_wide=prices_wide,
        rs_rating_wide=rs_rating_wide,
        blue_dot_wide=blue_dot_wide,
        config=minervini_cfg,
    )

    if pass_mask.empty:
        print("Error: 스크리닝 결과 없음", file=sys.stderr)
        return 4

    print(f"[kr_minervini_update] 스크리닝 완료: {pass_mask.shape[0]} 거래일 x {pass_mask.shape[1]} 종목")

    # 5. 저장할 거래일 결정 (최근 N일)
    all_dates = prices_wide.index.tolist()
    if len(all_dates) > args.days:
        save_dates = all_dates[-args.days:]
    else:
        save_dates = all_dates

    print(f"[kr_minervini_update] 저장 대상: 최근 {len(save_dates)} 거래일")

    # RS Rating 누락 날짜 경고
    if rs_rating_wide is not None and not rs_rating_wide.empty:
        rs_dates_set = set(str(d.date()) if hasattr(d, 'date') else str(d) for d in rs_rating_wide.index)
        missing = [d for d in save_dates if (str(d.date()) if hasattr(d, 'date') else str(d)) not in rs_dates_set]
        if missing:
            print(f"WARNING: RS Rating 누락 날짜 {len(missing)}일 발견. kr_rs_update.py를 먼저 실행하세요.")
            print(f"  누락 날짜 예시: {missing[:5]}")

    # 6. 통과 종목만 long-form 변환
    save_idx = pd.DatetimeIndex([pd.Timestamp(d) for d in save_dates])
    available = pass_mask.index.intersection(save_idx)
    if available.empty:
        print("Warning: 저장할 데이터 없음")
        return 0

    subset = pass_mask.loc[available]
    subset.index.name = "date"

    # melt: wide → long (통과한 종목만)
    melted = subset.reset_index().melt(
        id_vars=["date"],
        var_name="symbol",
        value_name="pass",
    )

    # 통과한 종목만 필터링 (pass == True)
    melted = melted[melted["pass"] == True]
    melted = melted.drop(columns=["pass"])

    if melted.empty:
        print("Warning: 통과한 종목 없음")
        return 0

    # RS Rating, Blue Dot 값 추출 (날짜+심볼 기준)
    if rs_rating_wide is not None and not rs_rating_wide.empty:
        rs_aligned = rs_rating_wide.reindex_like(prices_wide)
        rs_stacked = rs_aligned.stack().reset_index()
        rs_stacked.columns = ["date", "symbol", "rs_rating"]
        melted = melted.merge(rs_stacked, on=["date", "symbol"], how="left")
    else:
        melted["rs_rating"] = None

    if blue_dot_wide is not None and not blue_dot_wide.empty:
        bd_aligned = blue_dot_wide.reindex_like(prices_wide)
        bd_stacked = bd_aligned.stack().reset_index()
        bd_stacked.columns = ["date", "symbol", "is_blue_dot"]
        melted = melted.merge(bd_stacked, on=["date", "symbol"], how="left")
    else:
        melted["is_blue_dot"] = None

    # market 매핑
    melted["market"] = melted["symbol"].map(symbol_market_map).fillna("KOSPI")
    melted["date"] = pd.to_datetime(melted["date"]).dt.date

    # screen_config_hash 생성
    screen_hash = params_hash("minervini_screen", minervini_cfg)
    melted["screen_config_hash"] = screen_hash
    melted["failed_reason"] = None

    # conditions_met: 각 (symbol, date) 쌍에 대해 8개 조건 pass/fail JSON 생성
    def _build_conditions_met(symbol: str, date_val, conds: dict) -> str:
        result = {}
        for key, mask_df in conds.items():
            try:
                val = mask_df.at[pd.Timestamp(date_val), symbol]
                result[key] = False if pd.isna(val) else bool(val)
            except KeyError:
                result[key] = False
        return json.dumps(result)

    melted["conditions_met"] = melted.apply(
        lambda row: _build_conditions_met(row["symbol"], row["date"], conditions),
        axis=1,
    )

    # 컬럼 순서 정리
    result_df = melted[["symbol", "date", "market", "rs_rating", "is_blue_dot", "conditions_met", "screen_config_hash", "failed_reason"]]

    print(f"[kr_minervini_update] 저장할 레코드 수: {len(result_df)}")

    # 7. DB에 INSERT ONLY 저장
    DBManager.upsert_dataframe(
        engine=engine,
        df=result_df,
        table="minervini_screen_results_kr",
        mode="insert_only",
        unique_keys=("symbol", "date", "screen_config_hash"),
    )

    print("[kr_minervini_update] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
