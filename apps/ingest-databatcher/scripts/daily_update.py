# scripts/daily_update.py
from __future__ import annotations

"""
일일 증분 업데이트 스크립트 (개선 버전)

처리 흐름:
1. 최근 30일 가격 데이터 수집 (INSERT ONLY로 기존 데이터 보존)
2. DB에서 최근 250일 가격 데이터 조회
3. 250일치 전체에 대해 지표 계산
4. 최신 날짜부터 역순으로 처리, 완료된 날짜 만나면 중단

실행 예시:
    python scripts/daily_update.py --symbols 005930 000660
    python scripts/daily_update.py --all
    python scripts/daily_update.py --all --market KOSPI --top 100
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any
import pandas as pd
from sqlalchemy.engine import Engine

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.date_utils import DateUtils
from core.symbol_loader import load_symbols_with_details
from core.indicator_checker import IndicatorChecker
from core.price_loader import load_price_data
from collectors.kr_stock import KRStockCollector
from collectors.kr_etf import KREtfCollector

# 레지스트리에 지표를 등록하려면 모듈 import 가 필요합니다.
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver


def build_pipeline(cfg) -> IndicatorPipeline:
    specs_cfg = (cfg.get("indicators", {}).get("pipeline") or [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def extract_indicators_for_date(
    symbol: str,
    target_date,  # date object
    outputs: dict,  # {key: pd.Series}
    pipeline: IndicatorPipeline,
    market: str
) -> pd.DataFrame:
    """
    계산된 지표(outputs)에서 특정 날짜의 것만 추출하여 long-form으로 변환.

    Args:
        symbol: 종목코드
        target_date: 추출할 날짜 (date 객체)
        outputs: pipeline.run()의 결과 {key: Series}
        pipeline: long-form 변환용
        market: 시장 구분 (KOSPI/KOSDAQ/KONEX) - 필수

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
        source="pykrx",
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
    collector: Any,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    checker: IndicatorChecker,
    engine: Engine,
    market: str
) -> None:
    """
    단일 종목에 대한 일일 업데이트 처리.

    Contract:
    - 입력 범위: end_date 기준 최근 30일 가격 수집 + 최근 250일(및 warmup) 지표 계산
    - 저장 정책: 가격/지표 모두 insert_only (기존 데이터 덮어쓰기 없음)
    - 중단 조건: 최신일 역순 처리 중 해당 날짜 지표가 이미 완료면 즉시 중단

    흐름:
    1. 최근 30일 가격 수집 및 INSERT ONLY
    2. DB에서 최근 250일 데이터 조회
    3. 250일치 전체에 대해 지표 계산
    4. 최신 날짜부터 역순으로 INSERT ONLY, 완료된 날짜 만나면 중단

    Args:
        symbol: 종목코드
        end_date: 기준 종료일
        collector: Collector 인스턴스(KRStockCollector 또는 KREtfCollector)
        pipeline: IndicatorPipeline 인스턴스
        saver: IndicatorSaver 인스턴스
        checker: IndicatorChecker 인스턴스
        engine: SQLAlchemy engine
        market: 시장 구분 (KOSPI/KOSDAQ/KONEX) - 필수
    """
    # ========================================
    # STEP 1: 최근 30일 가격 수집 (INSERT ONLY)
    # ========================================
    start_30 = end_date - timedelta(days=30)

    df_new_price = collector.fetch(symbol, start=start_30, end=end_date, market=market)

    if df_new_price is not None and not df_new_price.empty:
        df_new_price = collector.validate(df_new_price)

        if df_new_price is not None and not df_new_price.empty:
            # INSERT ONLY: 기존 데이터 보존
            price_rows = collector.save(df_new_price, symbol, mode="insert_only")
            print(f"{symbol}: 가격 {price_rows}건 처리(insert-only)")

    # ========================================
    # STEP 2: DB에서 최근 250일 데이터 조회
    # ========================================
    start_250 = end_date - timedelta(days=250)

    df_250 = load_price_data(engine, symbol, start_250, end_date)

    if df_250 is None or df_250.empty:
        print(f"{symbol}: DB에 가격 데이터 없음, 스킵")
        return

    # ========================================
    # STEP 3: 지표 계산 (warmup 포함)
    # ========================================
    warmup = pipeline.warmup_days()
    start_with_warmup = start_250 - timedelta(days=warmup)

    # Warmup을 위한 추가 데이터 로드
    df_full = load_price_data(engine, symbol, start_with_warmup, end_date)

    if df_full is None or df_full.empty:
        print(f"{symbol}: warmup 데이터 부족, 스킵")
        return

    # 지표 계산 준비 (DatetimeIndex 설정)
    dfp = df_full.copy()
    dfp["date"] = pd.to_datetime(dfp["date"])
    dfp.set_index("date", inplace=True)

    # 전체 구간에 대해 지표 계산
    outputs = pipeline.run(dfp)

    if not outputs:
        print(f"{symbol}: 지표 계산 결과 없음")
        return

    # ========================================
    # STEP 4: 최신 날짜부터 역순 처리
    # ========================================
    # 250일 구간의 날짜 목록 (역순)
    dates_desc = sorted(df_250["date"].unique(), reverse=True)

    total_upserted = 0
    processed_dates = 0

    for target_date in dates_desc:
        # 4-1. 해당 날짜의 모든 지표가 이미 완료되었는지 체크
        if checker.is_complete(symbol, target_date):
            print(f"{symbol}: {target_date} 모든 지표 완료 → 중단")
            break

        # 4-2. 해당 날짜의 지표만 추출
        df_long_date = extract_indicators_for_date(
            symbol=symbol,
            target_date=target_date,
            outputs=outputs,
            pipeline=pipeline,
            market=market
        )

        if df_long_date is None or df_long_date.empty:
            # 해당 날짜의 지표 계산 실패 (warmup 부족 등)
            continue

        # 4-3. INSERT ONLY (기존 데이터 보존)
        rows = saver.save_long(df_long_date, mode="insert_only")
        total_upserted += rows
        processed_dates += 1

    print(f"{symbol}: {processed_dates}개 날짜 처리, 지표 {total_upserted}건 저장")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="KRX 일일 업데이트")
    p.add_argument("--symbols", nargs="*", default=None,
                   help="수집할 심볼 리스트 (미지정 시 --all 필요)")
    p.add_argument("--start", default=None,
                   help="수집 시작일(YYYY-MM-DD). 미지정 시 최신일자 기반 계산")
    p.add_argument("--end", default=None,
                   help="수집 종료일(YYYY-MM-DD). 미지정 시 마지막 마감 완료 영업일")
    # 신규 옵션
    p.add_argument("--all", action="store_true",
                   help="symbol_master의 모든 ACTIVE 종목 수집")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "KONEX", "ETF", "ALL"],
                   default="ALL", help="수집할 마켓 (default: ALL, --all과 함께 사용)")
    p.add_argument("--top", type=int, default=None,
                   help="시가총액 상위 N개만 수집 (--all과 함께 사용)")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # Validation: --symbols 또는 --all 중 하나는 필수
    if not args.symbols and not args.all:
        print("Error: --symbols 또는 --all 중 하나를 지정해야 합니다.", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python scripts/daily_update.py --symbols 005930 000660", file=sys.stderr)
        print("  python scripts/daily_update.py --all", file=sys.stderr)
        print("  python scripts/daily_update.py --all --market KOSPI", file=sys.stderr)
        sys.exit(2)

    cfg = load_settings()
    db_cfg = DBConfig(**cfg["database"]) if cfg.get("database") else None
    if not db_cfg:
        print("database 설정이 필요합니다(apps/ingest-databatcher/config/settings*.yaml 또는 DATABASE_URL).", file=sys.stderr)
        sys.exit(2)

    engine = DBManager.get_engine(db_cfg)

    du = DateUtils(cfg.get("runtime", {}).get("timezone", "Asia/Seoul"))

    # 종료일 계산 (기본: 마지막 마감 완료 영업일)
    mk_close = cfg.get("markets", {}).get("close_times", {}).get("XKRX", "16:00")
    buffer_min = int(cfg.get("markets", {}).get("safe_delay_minutes", 30))
    last_biz = du.get_last_closed_business_day("XKRX", mk_close, buffer_min)
    end_date = pd.to_datetime(args.end).date() if args.end else last_biz

    # 종목 목록 결정
    if args.all:
        symbols = load_symbols_with_details(engine, market=args.market, top=args.top)
        if not symbols:
            print("Error: symbol_master에서 ACTIVE 종목을 찾을 수 없습니다.", file=sys.stderr)
            print("먼저 'python scripts/sync_symbol_master.py'를 실행하세요.", file=sys.stderr)
            sys.exit(2)
        print(f"Loaded {len(symbols)} symbols from symbol_master (market={args.market})")
    else:
        # Legacy mode: --symbols 옵션 사용 시
        # 각 심볼에 대해 symbol_master에서 market 정보 조회
        from sqlalchemy import text
        symbols = []
        skipped = []
        for sym in args.symbols:
            sql = "SELECT symbol, name, market FROM symbol_master WHERE symbol = :symbol AND status = 'ACTIVE'"
            with engine.connect() as conn:
                result = conn.execute(text(sql), {"symbol": sym})
                row = result.fetchone()
                if row:
                    symbols.append({"symbol": row[0], "name": row[1], "market": row[2]})
                else:
                    # symbol_master에 없는 경우 경고 후 건너뛰기
                    print(f"Warning: {sym} not found in symbol_master (or not ACTIVE), skipping", file=sys.stderr)
                    skipped.append(sym)

        if not symbols:
            print("Error: 처리할 종목이 없습니다. symbol_master에서 ACTIVE 종목을 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(2)

        print(f"Processing {len(symbols)} symbols from --symbols")
        if skipped:
            print(f"Skipped {len(skipped)} symbols: {', '.join(skipped)}")

    # 초기화
    stock_collector = KRStockCollector(engine)
    etf_collector = KREtfCollector(engine)
    pipeline = build_pipeline(cfg)
    saver = IndicatorSaver(engine, table_long=cfg.get("indicators", {}).get("materialization", {}).get("table_long", "stock_indicators"))
    checker = IndicatorChecker(engine, cfg)

    # 각 종목 처리
    for symbol_info in symbols:
        symbol = symbol_info["symbol"]
        market = symbol_info["market"]
        collector = etf_collector if market == "ETF" else stock_collector
        try:
            process_symbol(
                symbol=symbol,
                end_date=end_date,
                collector=collector,
                pipeline=pipeline,
                saver=saver,
                checker=checker,
                engine=engine,
                market=market
            )
        except Exception as e:
            print(f"[daily_update] {symbol}: Error - {e}")
            continue


if __name__ == "__main__":
    main()
