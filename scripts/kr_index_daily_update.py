#!/usr/bin/env python3
"""
KR 지수 일일 증분 업데이트 스크립트

처리 흐름:
1. 최근 50일 가격 데이터 수집 (INSERT ONLY로 기존 데이터 보존)
2. DB에서 최근 250일 가격 데이터 조회
3. 250일치 전체에 대해 지표 계산
4. 최신 날짜부터 역순으로 처리, 완료된 날짜 만나면 중단

실행 예시:
    python scripts/kr_index_daily_update.py --all
    python scripts/kr_index_daily_update.py --all --market KOSPI
    python scripts/kr_index_daily_update.py --symbols 1001 2001
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path
import pandas as pd
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.date_utils import DateUtils
from core.kr_index_symbol_loader import load_kr_index_symbols_with_details
from core.indicator_checker import IndicatorChecker
from core.price_loader import load_price_data
from collectors.kr_index import KRIndexCollector

# Register indicators
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

# kr_index_prices 테이블에서 조회할 컬럼 (adj_close 없음)
INDEX_PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def build_pipeline(cfg) -> IndicatorPipeline:
    specs_cfg = cfg.get("indicators_kr_index", {}).get("pipeline", [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def extract_indicators_for_date(
    symbol: str,
    target_date,
    outputs: dict,
    pipeline: IndicatorPipeline,
    market: str,
) -> pd.DataFrame:
    """
    계산된 지표(outputs)에서 특정 날짜의 것만 추출하여 long-form으로 변환.
    """
    target_dt = pd.Timestamp(pd.to_datetime(target_date)).normalize()

    filtered = {}
    for key, series in outputs.items():
        if target_dt in pd.DatetimeIndex(series.index).normalize():
            val = series.reindex(pd.DatetimeIndex(series.index).normalize()).loc[target_dt]
            filtered[key] = pd.Series([val], index=[target_dt], name=series.name)

    if not filtered:
        return pd.DataFrame()

    df_long = pipeline.to_long_dataframe(
        symbol=symbol,
        market=market,
        source="yfinance",
        outputs=filtered,
        keep_nan=True,
    )

    if not df_long.empty and 'date' in df_long.columns:
        df_long['date'] = pd.to_datetime(df_long['date']).dt.normalize().dt.date

    return df_long


def process_index(
    symbol: str,
    end_date,
    collector: KRIndexCollector,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    checker: IndicatorChecker,
    engine: Engine,
    market: str,
) -> None:
    """
    단일 지수에 대한 일일 업데이트 처리.

    Contract:
    - 입력 범위: end_date 기준 최근 50일 가격 수집 + 최근 250일(및 warmup) 지표 계산
    - 저장 정책: 가격/지표 모두 insert_only (기존 데이터 덮어쓰기 없음)
    - 중단 조건: 최신일 역순 처리 중 해당 날짜 지표가 이미 완료면 즉시 중단

    흐름:
    1. 최근 50일 가격 수집 및 INSERT ONLY
    2. DB에서 최근 250일 데이터 조회
    3. 250일치 전체에 대해 지표 계산
    4. 최신 날짜부터 역순으로 INSERT ONLY, 완료된 날짜 만나면 중단
    """
    # STEP 1: 최근 50일 가격 수집 (INSERT ONLY)
    start_50 = end_date - timedelta(days=50)

    df_new_price = collector.fetch(symbol, start=start_50, end=end_date, market=market)

    if df_new_price is not None and not df_new_price.empty:
        df_new_price = collector.validate(df_new_price)

        if df_new_price is not None and not df_new_price.empty:
            price_rows = collector.save(df_new_price, symbol, mode="insert_only")
            print(f"{symbol}: 가격 {price_rows}건 처리(insert-only)")

    # STEP 2: DB에서 최근 250일 데이터 조회
    start_250 = end_date - timedelta(days=250)

    df_250 = load_price_data(
        engine, symbol, start_250, end_date,
        table="kr_index_prices",
        columns=INDEX_PRICE_COLUMNS,
    )

    if df_250 is None or df_250.empty:
        print(f"{symbol}: DB에 가격 데이터 없음, 스킵")
        return

    # STEP 3: 지표 계산 (warmup 포함)
    warmup = pipeline.warmup_days()
    start_with_warmup = start_250 - timedelta(days=warmup)

    df_full = load_price_data(
        engine, symbol, start_with_warmup, end_date,
        table="kr_index_prices",
        columns=INDEX_PRICE_COLUMNS,
    )

    if df_full is None or df_full.empty:
        print(f"{symbol}: warmup 데이터 부족, 스킵")
        return

    # DatetimeIndex 설정
    dfp = df_full.copy()
    dfp["date"] = pd.to_datetime(dfp["date"])
    dfp.set_index("date", inplace=True)

    outputs = pipeline.run(dfp)

    if not outputs:
        print(f"{symbol}: 지표 계산 결과 없음")
        return

    # STEP 4: 최신 날짜부터 역순 처리
    dates_desc = sorted(df_250["date"].unique(), reverse=True)

    total_upserted = 0
    processed_dates = 0

    for target_date in dates_desc:
        if checker.is_complete(symbol, target_date):
            print(f"{symbol}: {target_date} 모든 지표 완료 → 중단")
            break

        df_long_date = extract_indicators_for_date(
            symbol=symbol,
            target_date=target_date,
            outputs=outputs,
            pipeline=pipeline,
            market=market,
        )

        if df_long_date is None or df_long_date.empty:
            continue

        rows = saver.save_long(df_long_date, mode="insert_only")
        total_upserted += rows
        processed_dates += 1

    print(f"{symbol}: {processed_dates}개 날짜 처리, 지표 {total_upserted}건 저장")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="KR 지수 일일 업데이트")
    p.add_argument("--symbols", nargs="*", default=None,
                   help="수집할 지수코드 리스트 (미지정 시 --all 필요)")
    p.add_argument("--end", default=None,
                   help="수집 종료일(YYYY-MM-DD). 미지정 시 마지막 마감 완료 영업일")
    p.add_argument("--all", action="store_true",
                   help="kr_index_master의 모든 ACTIVE 지수 수집")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "ALL"],
                   default="ALL", help="수집할 마켓 (default: ALL, --all과 함께 사용)")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not args.symbols and not args.all:
        print("Error: --symbols 또는 --all 중 하나를 지정해야 합니다.", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python scripts/kr_index_daily_update.py --all", file=sys.stderr)
        print("  python scripts/kr_index_daily_update.py --symbols 1001 2001", file=sys.stderr)
        sys.exit(2)

    cfg = load_settings()
    db_cfg = DBConfig(**cfg.get("database", {}))
    engine = DBManager.get_engine(db_cfg)

    du = DateUtils(cfg.get("runtime", {}).get("timezone", "Asia/Seoul"))

    # 종료일 계산 (기본: 마지막 마감 완료 영업일)
    mk_close = cfg.get("markets", {}).get("close_times", {}).get("XKRX", "16:00")
    buffer_min = int(cfg.get("markets", {}).get("safe_delay_minutes", 30))
    last_biz = du.get_last_closed_business_day("XKRX", mk_close, buffer_min)
    end_date = pd.to_datetime(args.end).date() if args.end else last_biz

    # 지수 목록 결정
    if args.all:
        indices = load_kr_index_symbols_with_details(engine, market=args.market)
        if not indices:
            print("Error: kr_index_master에서 ACTIVE 지수를 찾을 수 없습니다.", file=sys.stderr)
            print("먼저 'python scripts/kr_index_sync_master.py'를 실행하세요.", file=sys.stderr)
            sys.exit(2)
        print(f"Loaded {len(indices)} indices from kr_index_master (market={args.market})")
    else:
        from sqlalchemy import text as sql_text
        indices = []
        for sym in args.symbols:
            sql = "SELECT symbol, name, market FROM kr_index_master WHERE symbol = :symbol AND status = 'ACTIVE'"
            with engine.connect() as conn:
                result = conn.execute(sql_text(sql), {"symbol": sym})
                row = result.fetchone()
                if row:
                    indices.append({"symbol": row[0], "name": row[1], "market": row[2]})
                else:
                    print(f"Warning: {sym} not found in kr_index_master, skipping", file=sys.stderr)

        if not indices:
            print("Error: 처리할 지수가 없습니다.", file=sys.stderr)
            sys.exit(2)

    # 초기화
    collector = KRIndexCollector(engine)
    pipeline = build_pipeline(cfg)
    table_long = cfg.get("indicators_kr_index", {}).get("materialization", {}).get("table_long", "kr_index_indicators")
    saver = IndicatorSaver(engine, table_long=table_long)
    checker = IndicatorChecker(engine, cfg, table="kr_index_indicators", config_key="indicators_kr_index")

    # 각 지수 처리
    failed_symbols: list[str] = []
    for idx_info in indices:
        symbol = idx_info["symbol"]
        market = idx_info["market"]
        try:
            process_index(
                symbol=symbol,
                end_date=end_date,
                collector=collector,
                pipeline=pipeline,
                saver=saver,
                checker=checker,
                engine=engine,
                market=market,
            )
        except Exception as e:
            print(f"[kr_index_daily_update] {symbol}: Error - {e}")
            failed_symbols.append(symbol)
            continue

    if failed_symbols:
        print(f"[kr_index_daily_update] 실패 {len(failed_symbols)}개: {', '.join(failed_symbols)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
