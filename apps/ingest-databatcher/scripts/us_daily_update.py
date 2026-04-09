#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US 주식 일봉 daily update

정책:
- 대상 심볼 결정 우선순위:
  1) --all 지정 시: us_symbol_master의 ACTIVE 전체
  2) --symbols 지정 시: 해당 심볼만
- 최근 50일만 업데이트 (고정)
- 기본 end date:
  - ET 18:00 이상이면 ET 오늘
  - ET 18:00 이전이면 ET 어제
- 가격: insert_only
- 지표: insert_only
- 지표는 keep_nan=True로 row를 만들고, NaN은 DB NULL로 저장

실행 예:
    python scripts/us_daily_update.py --symbols AAPL MSFT --with-indicators
    python scripts/us_daily_update.py --all --with-indicators
    python scripts/us_daily_update.py --all --market NASDAQ --with-indicators
    python scripts/us_daily_update.py --all --top 100 --with-indicators
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.us_stock import USStockCollector
from core.config_loader import (
    load_settings,
    resolve_indicator_source,
    resolve_source_strategy,
    VALID_SOURCE_STRATEGIES,
)
from core.db_manager import DBManager, DBConfig
from core.us_symbol_loader import load_us_symbols_with_details
from core.date_utils import default_end_date_us_eastern_cutoff
from core.indicator_checker import IndicatorChecker
from core.price_loader import load_price_data
from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver
from sqlalchemy import text
from sqlalchemy.engine import Engine

# 지표 registry 등록
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

# 고정 업데이트 범위
LOOKBACK_DAYS = 50


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="US Stock daily update")
    p.add_argument("--all", action="store_true",
                   help="us_symbol_master의 모든 ACTIVE 종목 수집")
    p.add_argument("--symbols", nargs="+", default=None,
                   help="수집할 심볼 리스트 (예: AAPL MSFT)")
    p.add_argument("--market", choices=["NYSE", "NASDAQ", "ETF", "ALL"],
                   default="ALL", help="수집할 마켓 (--all과 함께 사용, default: ALL)")
    p.add_argument("--top", type=int, default=None,
                   help="상위 N개만 수집 (--all과 함께 사용)")
    p.add_argument("--end", default=None,
                   help="YYYY-MM-DD (US Eastern 기준). default: ET 18:00 cutoff 규칙")
    p.add_argument("--with-indicators", action="store_true",
                   help="지표 계산 포함")
    p.add_argument("--source-strategy", choices=VALID_SOURCE_STRATEGIES, default=None,
                   help="가격 수집 소스 전략 override (fdr/yfinance/fdr_then_yfinance)")
    return p.parse_args(argv)


def build_us_pipeline(cfg: dict) -> IndicatorPipeline:
    """US 주식용 지표 파이프라인 생성"""
    specs_cfg = cfg.get("indicators_us", {}).get("pipeline", [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def extract_indicators_for_date(
    symbol: str,
    target_date,  # date object
    outputs: dict,  # {key: pd.Series}
    pipeline: IndicatorPipeline,
    market: str,
    source: str,
) -> pd.DataFrame:
    """
    계산된 지표(outputs)에서 특정 날짜의 것만 추출하여 long-form으로 변환.

    Args:
        symbol: 종목코드
        target_date: 추출할 날짜 (date 객체)
        outputs: pipeline.run()의 결과 {key: Series}
        pipeline: long-form 변환용
        market: 시장 구분 (NYSE/NASDAQ/ETF) - 필수

    Returns:
        해당 날짜의 지표만 포함된 long-form DataFrame
    """
    target_dt = pd.Timestamp(pd.to_datetime(target_date)).normalize()

    # 특정 날짜의 값만 필터링
    filtered = {}
    for key, series in outputs.items():
        if target_dt in pd.DatetimeIndex(series.index).normalize():
            # 단일 값을 Series로 만들기
            # series.index와 동일한 타입으로 조회되도록 normalize된 timestamp로 재인덱싱
            val = series.reindex(pd.DatetimeIndex(series.index).normalize()).loc[target_dt]
            filtered[key] = pd.Series([val], index=[target_dt], name=series.name)

    if not filtered:
        return pd.DataFrame()

    # Long-form 변환
    df_long = pipeline.to_long_dataframe(
        symbol=symbol,
        market=market,
        source=source,
        outputs=filtered,
        keep_nan=True,
    )

    # date 컬럼을 date 타입으로 변환 (yyyy-mm-dd 형식)
    if not df_long.empty and 'date' in df_long.columns:
        df_long['date'] = pd.to_datetime(df_long['date']).dt.normalize().dt.date

    return df_long


def process_symbol(
    symbol: str,
    end_date,  # date object
    collector: USStockCollector,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    checker: IndicatorChecker,
    engine: Engine,
    market: str
) -> None:
    """
    단일 종목에 대한 일일 업데이트 처리.

    Contract:
    - 입력 범위: end_date 기준 최근 50일 가격 수집 + 최근 250일(및 warmup) 지표 계산
    - 저장 정책: 가격/지표 모두 insert_only (기존 데이터 덮어쓰기 없음)
    - 중단 조건: 최신일 역순 처리 중 해당 날짜 지표가 이미 완료면 즉시 중단

    흐름:
    1. 최근 50일 가격 수집 및 INSERT ONLY
    2. DB에서 최근 250일 가격 데이터 조회
    3. 250일치 전체에 대해 지표 계산
    4. 최신 날짜부터 역순으로 INSERT ONLY, 완료된 날짜 만나면 중단

    Args:
        symbol: 종목코드
        end_date: 기준 종료일
        collector: USStockCollector 인스턴스
        pipeline: IndicatorPipeline 인스턴스
        saver: IndicatorSaver 인스턴스
        checker: IndicatorChecker 인스턴스
        engine: SQLAlchemy engine
        market: 시장 구분 (NYSE/NASDAQ/ETF) - 필수
    """
    # ========================================
    # STEP 1: 최근 50일 가격 수집 (INSERT ONLY)
    # ========================================
    start_50 = end_date - timedelta(days=LOOKBACK_DAYS)

    df_new_price = collector.fetch(symbol, start=start_50, end=end_date, market=market)

    if df_new_price is not None and not df_new_price.empty:
        # date 타입
        df_new_price["date"] = pd.to_datetime(df_new_price["date"]).dt.date

        # INSERT ONLY: 기존 데이터 보존
        new_rows = DBManager.upsert_dataframe(engine, df_new_price, table="us_stock_prices", mode="insert_only")
        print(f"  {symbol}: 가격 {new_rows}건 처리(insert-only)")

    indicator_source = resolve_indicator_source(collector)

    # ========================================
    # STEP 2: DB에서 최근 250일 데이터 조회
    # ========================================
    start_250 = end_date - timedelta(days=250)

    df_250 = load_price_data(engine, symbol, start_250, end_date, table="us_stock_prices")

    if df_250 is None or df_250.empty:
        print(f"  {symbol}: DB에 가격 데이터 없음, 스킵")
        return

    # ========================================
    # STEP 3: 지표 계산 (warmup 포함)
    # ========================================
    warmup = pipeline.warmup_days()
    start_with_warmup = start_250 - timedelta(days=warmup)

    # Warmup을 위한 추가 데이터 로드
    df_full = load_price_data(engine, symbol, start_with_warmup, end_date, table="us_stock_prices")

    if df_full is None or df_full.empty:
        print(f"  {symbol}: warmup 데이터 부족, 스킵")
        return

    # 지표 계산 준비 (DatetimeIndex 설정)
    dfp = df_full.copy()
    dfp["date"] = pd.to_datetime(dfp["date"])
    dfp.set_index("date", inplace=True)

    # 전체 구간에 대해 지표 계산
    outputs = pipeline.run(dfp)

    if not outputs:
        print(f"  {symbol}: 지표 계산 결과 없음")
        return

    # ========================================
    # STEP 4: 최신 날짜부터 역순 처리
    # ========================================
    # 250일 구간의 날짜 목록 (역순)
    dates_desc = sorted(df_250["date"].unique(), reverse=True)

    total_inserted = 0
    processed_dates = 0

    for target_date in dates_desc:
        # 4-1. 해당 날짜의 모든 지표가 이미 완료되었는지 체크
        if checker.is_complete(symbol, target_date):
            print(f"  {symbol}: {target_date} 모든 지표 완료 → 중단")
            break

        # 4-2. 해당 날짜의 지표만 추출
        df_long_date = extract_indicators_for_date(
            symbol=symbol,
            target_date=target_date,
            outputs=outputs,
            pipeline=pipeline,
            market=market,
            source=indicator_source,
        )

        if df_long_date is None or df_long_date.empty:
            # 해당 날짜의 지표 계산 실패 (warmup 부족 등)
            continue

        # 4-3. INSERT ONLY (기존 데이터 보존)
        rows = saver.save_long(df_long_date, mode="insert_only")
        total_inserted += rows
        processed_dates += 1

    print(f"  {symbol}: {processed_dates}개 날짜 처리, 지표 {total_inserted}건 저장")


def main(argv=None) -> int:
    args = parse_args(argv)

    # Validation: --symbols 또는 --all 중 하나는 필수
    if not args.symbols and not args.all:
        print("Error: --symbols 또는 --all 중 하나를 지정해야 합니다.", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python scripts/us_daily_update.py --symbols AAPL MSFT --with-indicators", file=sys.stderr)
        print("  python scripts/us_daily_update.py --all --with-indicators", file=sys.stderr)
        return 2

    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))
    source_strategy = resolve_source_strategy(cfg, args.source_strategy, "us_stock")

    # 대상 심볼 결정
    if args.all:
        symbols = load_us_symbols_with_details(engine, market=args.market, top=args.top)
        source_desc = f"--all (us_symbol_master ACTIVE, market={args.market})"
    else:
        # --symbols는 us_symbol_master에서 market/name을 조회해 보정
        symbols = []
        skipped = []
        for raw in args.symbols:
            sym = raw.upper().strip() if raw else ""
            if not sym:
                continue
            sql = text(
                "SELECT symbol, name, market FROM us_symbol_master "
                "WHERE symbol = :symbol AND status = 'ACTIVE'"
            )
            with engine.connect() as conn:
                row = conn.execute(sql, {"symbol": sym}).fetchone()
            if row:
                symbols.append({"symbol": row[0], "name": row[1], "market": row[2]})
            else:
                skipped.append(sym)

        if skipped:
            print(f"Warning: us_symbol_master ACTIVE에 없는 심볼 스킵: {', '.join(skipped)}", file=sys.stderr)
        source_desc = "--symbols (market from us_symbol_master)"

    if not symbols:
        print(
            "Error: 처리할 US 심볼이 없습니다. --all 또는 --symbols를 지정하세요.",
            file=sys.stderr,
        )
        return 2

    if args.end:
        end_d: date = pd.to_datetime(args.end).date()
        end_desc = f"user-specified ({end_d})"
    else:
        cutoff_hhmm = cfg.get("markets", {}).get("us_daily_cutoff", "18:00")
        end_d = default_end_date_us_eastern_cutoff(cutoff_hhmm)
        end_desc = f"auto (ET cutoff {cutoff_hhmm})"
    start_d: date = end_d - timedelta(days=LOOKBACK_DAYS)

    print(f"[us_daily_update] targets={len(symbols)} source={source_desc}")
    print(f"[us_daily_update] end_date={end_d} ({end_desc})")
    print(f"[us_daily_update] range={start_d}..{end_d} days={LOOKBACK_DAYS} (fixed)")
    print(f"[us_daily_update] source_strategy={source_strategy}")

    # 초기화
    collector = USStockCollector(engine, source_strategy=source_strategy)
    pipeline = build_us_pipeline(cfg) if args.with_indicators else None
    saver = None
    checker = None

    if args.with_indicators and pipeline:
        table_long = cfg.get("indicators_us", {}).get("materialization", {}).get("table_long", "us_stock_indicators")
        saver = IndicatorSaver(engine, table_long=table_long)
        checker = IndicatorChecker(engine, cfg, config_key="indicators_us", table=table_long)

    # 각 종목 처리
    for sym_info in symbols:
        symbol = sym_info["symbol"]
        market = sym_info["market"]
        print(f"[us_daily_update] symbol={symbol}")

        try:
            if args.with_indicators and pipeline and saver and checker:
                # 새로운 방식: DB에서 250일 로드 → 지표 계산 → INSERT ONLY
                process_symbol(
                    symbol=symbol,
                    end_date=end_d,
                    collector=collector,
                    pipeline=pipeline,
                    saver=saver,
                    checker=checker,
                    engine=engine,
                    market=market
                )
            else:
                # 지표 계산 없이 가격만 업데이트 (legacy mode)
                df_price = collector.fetch(symbol, start=start_d, end=end_d, market=market)
                if df_price is None or df_price.empty:
                    print("  -> no price data")
                    continue

                # date 타입
                df_price["date"] = pd.to_datetime(df_price["date"]).dt.date

                price_rows = DBManager.upsert_dataframe(engine, df_price, table="us_stock_prices", mode="insert_only")
                print(f"  -> prices saved(insert_only) rows={price_rows}")

        except Exception as e:
            print(f"  -> Error: {e}")
            continue

    print("[us_daily_update] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
