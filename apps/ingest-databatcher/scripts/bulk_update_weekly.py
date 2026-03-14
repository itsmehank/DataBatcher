#!/usr/bin/env python3
"""
주봉 데이터 일괄 생성 스크립트

일봉 데이터를 주 단위로 집계하여 stock_prices_weekly 및 stock_indicators_weekly 테이블에 저장합니다.
최초 1회 실행하여 과거 전체 주봉 데이터를 생성합니다.

실행 예시:
    # 전체 마켓, DB 전체 기간 주봉 생성 (가장 일반적)
    python scripts/bulk_update_weekly.py

    # 전체 마켓, 특정 기간만 주봉 생성
    python scripts/bulk_update_weekly.py --start 2020-01-01 --end 2024-12-31

    # KOSPI만, DB 전체 기간 주봉 생성
    python scripts/bulk_update_weekly.py --market KOSPI

    # KOSDAQ 상위 100개만, 특정 기간
    python scripts/bulk_update_weekly.py --market KOSDAQ --top 100 --start 2024-01-01 --end 2024-12-31

주의:
    - 일봉 데이터가 DB에 먼저 존재해야 합니다 (bulk_update.py 선행 실행 필요)
    - 주봉 집계의 week_start/week_end는 해당 주의 첫/마지막 거래일입니다
    - --start와 --end는 함께 지정하거나 둘 다 생략해야 합니다
"""
from __future__ import annotations
import argparse
import sys
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.weekly_aggregation import aggregate_daily_to_weekly_trading_days

# Import indicator modules to register them
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

try:
    from tqdm import tqdm
except ImportError:
    print("Error: tqdm not installed. Run: pip install tqdm", file=sys.stderr)
    sys.exit(1)


# Setup logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
FAILED_LOG = LOG_DIR / "bulk_update_weekly_failed.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_symbols(
    engine: Engine,
    market: Optional[str] = None,
    top: Optional[int] = None
) -> List[Tuple[str, str, str]]:
    """
    DB에서 주봉 생성 대상 종목 목록 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/KONEX/ALL (default: ALL)
        top: 시가총액 상위 N개만 (default: None = 전체)

    Returns:
        [(symbol, name, market), ...] 리스트
    """
    sql = """
        SELECT symbol, name, market FROM symbol_master
        WHERE status = 'ACTIVE'
    """
    params: Dict[str, Any] = {}

    if market and market != "ALL":
        sql += " AND market = :market"
        params["market"] = market

    sql += " ORDER BY symbol"

    if top:
        sql += " LIMIT :top"
        params["top"] = int(top)

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.all()

    return [(row[0], row[1], row[2]) for row in rows]


def save_weekly_prices(engine: Engine, symbol: str, weekly_df: pd.DataFrame, market: str) -> tuple[int, int]:
    """
    주봉 가격 데이터를 DB에 저장

    Args:
        engine: SQLAlchemy engine
        symbol: 종목 코드
        weekly_df: 주봉 DataFrame
        market: 시장 구분 (KOSPI/KOSDAQ/KONEX)

    Returns:
        (시도 건수, 실제 INSERT 건수)
    """
    if weekly_df.empty:
        return 0, 0

    weekly_df = weekly_df.copy()
    weekly_df['symbol'] = symbol

    # 날짜를 문자열로 변환 (yyyy-mm-dd)
    weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%Y-%m-%d')
    weekly_df['week_end'] = pd.to_datetime(weekly_df['week_end']).dt.strftime('%Y-%m-%d')

    # 필요한 컬럼만 선택
    columns = ['symbol', 'week_start', 'week_end', 'open', 'high', 'low', 'close', 'volume']
    if 'adj_close' in weekly_df.columns:
        columns.insert(7, 'adj_close')
    if 'market' in weekly_df.columns:
        columns.append('market')
    if 'source' in weekly_df.columns:
        columns.append('source')

    save_df = weekly_df[columns]

    # INSERT ONLY (중복 무시)
    attempted_rows = 0
    inserted_rows = 0
    with engine.begin() as conn:
        for _, row in save_df.iterrows():
            sql = """
                INSERT IGNORE INTO stock_prices_weekly
                (symbol, week_start, week_end, open, high, low, close, adj_close, volume, market, source)
                VALUES (:symbol, :week_start, :week_end, :open, :high, :low, :close, :adj_close, :volume, :market, :source)
            """
            result = conn.execute(text(sql), {
                'symbol': row['symbol'],
                'week_start': row['week_start'],
                'week_end': row['week_end'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'adj_close': float(row['adj_close']) if 'adj_close' in row and pd.notna(row['adj_close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                'market': row.get('market', market),
                'source': row.get('source', 'pykrx')
            })
            attempted_rows += 1
            inserted_rows += max(result.rowcount or 0, 0)

    return attempted_rows, inserted_rows


def process_symbol(
    symbol: str,
    name: str,
    market: str,
    start: date,
    end: date,
    pipeline: Optional[IndicatorPipeline],
    saver: Optional[IndicatorSaver],
    engine: Engine
) -> Dict[str, Any]:
    """
    단일 종목의 주봉 데이터 생성 및 저장

    Contract:
    - 입력: 특정 symbol의 일봉 구간(start~end)
    - 출력: 시도/저장 건수 포함 처리 결과 딕셔너리
    - 주봉 키 규칙: core.weekly_aggregation.aggregate_daily_to_weekly_trading_days 기준

    Args:
        symbol: 종목 코드
        name: 종목명
        market: 시장 (KOSPI/KOSDAQ/...)
        start: 시작일
        end: 종료일
        pipeline: 지표 계산 파이프라인 (None이면 지표 계산 스킵)
        saver: 지표 저장 객체 (None이면 지표 저장 스킵)
        engine: SQLAlchemy engine

    Returns:
        처리 결과 딕셔너리
    """
    try:
        # 1. DB에서 일봉 데이터 조회
        sql = """
            SELECT date, open, high, low, close, adj_close, volume, market, source
            FROM stock_prices
            WHERE symbol = :symbol
              AND date >= :start
              AND date <= :end
            ORDER BY date ASC
        """

        with engine.connect() as conn:
            result = conn.execute(text(sql), {'symbol': symbol, 'start': start, 'end': end})
            daily_data = result.fetchall()

        if not daily_data:
            return {
                'symbol': symbol,
                'status': 'skip',
                'message': 'No daily data found'
            }

        # DataFrame으로 변환
        daily_df = pd.DataFrame(daily_data, columns=['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'market', 'source'])

        # 2. 주봉으로 집계
        weekly_df = aggregate_daily_to_weekly_trading_days(daily_df, skip_latest_week=True)

        if weekly_df.empty:
            return {
                'symbol': symbol,
                'status': 'skip',
                'message': 'No weekly data generated'
            }

        # 3. 주봉 가격 데이터 저장
        price_attempted, price_inserted = save_weekly_prices(engine, symbol, weekly_df, market)

        # 4. 주봉 지표 계산 및 저장
        indicator_rows = 0
        if pipeline is not None and saver is not None:
            # 지표 계산을 위한 OHLCV 데이터 준비
            indicator_df = weekly_df[['week_start', 'open', 'high', 'low', 'close', 'volume']].copy()
            indicator_df = indicator_df.rename(columns={'week_start': 'date'})
            indicator_df['date'] = pd.to_datetime(indicator_df['date'])

            # 지표 계산
            indicator_df = indicator_df.set_index('date')
            outputs = pipeline.run(indicator_df)

            # 지표 저장 (long-form으로 변환)
            indicator_long_df = pipeline.to_long_dataframe(
                symbol=symbol,
                market=market,
                source='pykrx',
                outputs=outputs,
                keep_nan=True,
            )

            if not indicator_long_df.empty:
                # date 컬럼을 date 타입으로 변환 (yyyy-mm-dd 형식)
                if 'date' in indicator_long_df.columns:
                    indicator_long_df['date'] = pd.to_datetime(indicator_long_df['date']).dt.date
                # 주봉 테이블은 'date' 대신 'week_start' 컬럼 사용
                indicator_long_df = indicator_long_df.rename(columns={'date': 'week_start'})
                indicator_rows = saver.save_long(indicator_long_df, mode="insert_only")

        return {
            'symbol': symbol,
            'status': 'success',
            'price_rows': price_inserted,
            'price_attempted_rows': price_attempted,
            'indicator_rows': indicator_rows
        }

    except Exception as e:
        logger.error(f"{symbol}: Error - {e}")
        return {
            'symbol': symbol,
            'status': 'error',
            'message': str(e)
        }


def write_failed_log(failed_results: List[Dict[str, Any]]) -> None:
    """실패한 종목 로그 기록"""
    if not failed_results:
        return

    with FAILED_LOG.open("w", encoding="utf-8") as f:
        f.write(f"# Bulk Weekly Update Failed Symbols - {datetime.now()}\n")
        for result in failed_results:
            symbol = result['symbol']
            msg = result.get('message', 'Unknown error')
            f.write(f"{symbol}: {msg}\n")

    logger.info(f"Failed symbols logged to: {FAILED_LOG}")


def get_date_range_from_db(engine: Engine, market: str) -> Tuple[date, date]:
    """
    stock_prices 테이블에서 최소/최대 날짜 조회

    Args:
        engine: SQLAlchemy engine
        market: 마켓 필터 (ALL/KOSPI/KOSDAQ/KONEX)

    Returns:
        (min_date, max_date) tuple

    Raises:
        ValueError: stock_prices 테이블이 비어있거나 해당 마켓에 데이터가 없는 경우
    """
    sql = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM stock_prices"
    params: Dict[str, Any] = {}

    # market이 ALL이 아니면 필터링 추가
    if market != "ALL":
        sql += " WHERE market = :market"
        params["market"] = market

    with engine.connect() as conn:
        result = conn.execute(text(sql), params).mappings().first()

        if not result or not result['min_date'] or not result['max_date']:
            if market == "ALL":
                raise ValueError(
                    "stock_prices 테이블이 비어있습니다. "
                    "bulk_update.py를 먼저 실행하여 일봉 데이터를 적재하세요."
                )
            else:
                raise ValueError(
                    f"stock_prices 테이블에 {market} 데이터가 없습니다. "
                    "bulk_update.py를 먼저 실행하여 일봉 데이터를 적재하세요."
                )

        return result['min_date'], result['max_date']


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="주봉 데이터 일괄 생성")
    parser.add_argument(
        "--start",
        help="시작일 (YYYY-MM-DD, 미입력시 DB 최소 날짜 자동 조회)"
    )
    parser.add_argument(
        "--end",
        help="종료일 (YYYY-MM-DD, 미입력시 DB 최대 날짜 자동 조회)"
    )
    parser.add_argument(
        "--market",
        default="ALL",
        choices=["ALL", "KOSPI", "KOSDAQ", "KONEX", "ETF"],
        help="마켓 선택 (기본값: ALL)"
    )
    parser.add_argument("--top", type=int, help="상위 N개 종목만")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Load configuration
    cfg = load_settings()
    db_cfg = DBConfig(**cfg['database'])
    engine = DBManager.get_engine(db_cfg)

    # Parse dates or get from DB
    try:
        if args.start and args.end:
            # 사용자가 기간 지정
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
            logger.info(f"사용자 지정 기간: {start_date} ~ {end_date}")
        elif args.start or args.end:
            # 하나만 지정된 경우 에러
            logger.error("--start와 --end는 함께 지정하거나 둘 다 생략해야 합니다")
            return 1
        else:
            # DB에서 전체 기간 조회 (market 필터 포함)
            logger.info(f"기간 미지정 - {args.market} 마켓의 전체 일봉 데이터를 주봉으로 변환합니다")
            start_date, end_date = get_date_range_from_db(engine, args.market)
            logger.info(f"DB 조회 기간: {start_date} ~ {end_date}")
    except ValueError as e:
        logger.error(f"날짜 처리 오류: {e}")
        return 1

    # Load symbols
    logger.info("Loading symbols from symbol_master...")
    symbols = load_symbols(engine, market=args.market, top=args.top)
    logger.info(f"Found {len(symbols)} symbols to process")

    if not symbols:
        logger.warning("No symbols to process")
        return 0

    # Build indicator pipeline (weekly)
    weekly_cfg = cfg.get('indicators_weekly', cfg.get('indicators')) or {}
    raw_pipeline = weekly_cfg.get('pipeline') or [] if weekly_cfg else []
    pipeline_specs = [IndicatorSpec(**spec) for spec in raw_pipeline]

    if pipeline_specs:
        pipeline = IndicatorPipeline(pipeline_specs)
        table_name = weekly_cfg.get('materialization', {}).get('table_long', 'stock_indicators_weekly')
        saver = IndicatorSaver(engine, table_long=table_name)
    else:
        pipeline = None
        saver = None
        logger.info("No indicator pipeline configured — prices only")

    # Process all symbols
    logger.info(f"Processing {len(symbols)} symbols from {start_date} to {end_date}...")
    success_count = 0
    skip_count = 0
    failed_results = []

    for symbol, name, market in tqdm(symbols, desc="Processing"):
        result = process_symbol(symbol, name, market, start_date, end_date, pipeline, saver, engine)

        if result['status'] == 'success':
            success_count += 1
            logger.info(
                f"{symbol}: 주봉 가격 시도 {result.get('price_attempted_rows', 0)}건, "
                f"신규 저장 {result['price_rows']}건, 지표 {result['indicator_rows']}건 저장"
            )
        elif result['status'] == 'skip':
            skip_count += 1
            logger.warning(f"{symbol}: {result.get('message', 'Skipped')}")
        else:
            failed_results.append(result)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Weekly Bulk Update Complete")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Skipped: {skip_count}")
    logger.info(f"  Failed:  {len(failed_results)}")
    logger.info("=" * 60)

    # Write failed log
    if failed_results:
        write_failed_log(failed_results)

    return 0 if not failed_results else 1


if __name__ == "__main__":
    sys.exit(main())
