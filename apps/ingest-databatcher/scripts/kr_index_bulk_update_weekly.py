#!/usr/bin/env python3
"""
KR 지수(KOSPI/KOSDAQ) 주봉 데이터 일괄 생성 스크립트

일봉 데이터(kr_index_prices)를 주 단위로 집계하여
kr_index_prices_weekly 및 kr_index_indicators_weekly 테이블에 저장합니다.

실행 예시:
    # 전체 기간 주봉 생성 (DB 전체 기간 자동 조회)
    python scripts/kr_index_bulk_update_weekly.py

    # 특정 기간만
    python scripts/kr_index_bulk_update_weekly.py --start 2020-01-01 --end 2024-12-31

    # KOSPI만
    python scripts/kr_index_bulk_update_weekly.py --market KOSPI

주의:
    - kr_index_prices에 일봉 데이터가 먼저 존재해야 합니다 (kr_index_bulk_update.py 선행 실행 필요)
    - --start와 --end는 함께 지정하거나 둘 다 생략해야 합니다
"""
from __future__ import annotations
import argparse
import sys
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.kr_index_symbol_loader import load_kr_index_symbols_with_details
from core.weekly_aggregation import aggregate_daily_to_weekly_trading_days

# Import indicator modules to register them
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

# Setup logging
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_date_range_from_db(engine: Engine, market: str) -> Tuple[date, date]:
    """
    kr_index_prices 테이블에서 최소/최대 날짜 조회

    Args:
        engine: SQLAlchemy engine
        market: 마켓 필터 (ALL/KOSPI/KOSDAQ)

    Returns:
        (min_date, max_date) tuple
    """
    sql = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM kr_index_prices"
    params: Dict[str, Any] = {}

    if market != "ALL":
        sql += " WHERE market = :market"
        params["market"] = market

    with engine.connect() as conn:
        result = conn.execute(text(sql), params).mappings().first()

        if not result or not result['min_date'] or not result['max_date']:
            if market == "ALL":
                raise ValueError(
                    "kr_index_prices 테이블이 비어있습니다. "
                    "kr_index_bulk_update.py를 먼저 실행하여 일봉 데이터를 적재하세요."
                )
            else:
                raise ValueError(
                    f"kr_index_prices 테이블에 {market} 데이터가 없습니다. "
                    "kr_index_bulk_update.py를 먼저 실행하여 일봉 데이터를 적재하세요."
                )

        return result['min_date'], result['max_date']


def save_weekly_prices(engine: Engine, symbol: str, weekly_df: pd.DataFrame, market: str) -> int:
    """
    주봉 가격 데이터를 kr_index_prices_weekly에 INSERT ONLY로 저장
    (adj_close 없음)
    """
    if weekly_df.empty:
        return 0

    weekly_df = weekly_df.copy()
    weekly_df['symbol'] = symbol

    weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.strftime('%Y-%m-%d')
    weekly_df['week_end'] = pd.to_datetime(weekly_df['week_end']).dt.strftime('%Y-%m-%d')

    with engine.begin() as conn:
        for _, row in weekly_df.iterrows():
            sql = """
                INSERT IGNORE INTO kr_index_prices_weekly
                (symbol, week_start, week_end, open, high, low, close, volume, market, source)
                VALUES (:symbol, :week_start, :week_end, :open, :high, :low, :close, :volume, :market, :source)
            """
            conn.execute(text(sql), {
                'symbol': row['symbol'],
                'week_start': row['week_start'],
                'week_end': row['week_end'],
                'open': float(row['open']) if pd.notna(row['open']) else None,
                'high': float(row['high']) if pd.notna(row['high']) else None,
                'low': float(row['low']) if pd.notna(row['low']) else None,
                'close': float(row['close']) if pd.notna(row['close']) else None,
                'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                'market': row.get('market', market),
                'source': row.get('source', 'yfinance'),
            })

    return len(weekly_df)


def process_index(
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
    단일 지수의 주봉 데이터 생성 및 저장
    """
    try:
        # 1. DB에서 일봉 데이터 조회 (adj_close 없음)
        sql = """
            SELECT date, open, high, low, close, volume, market, source
            FROM kr_index_prices
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

        daily_df = pd.DataFrame(daily_data, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'market', 'source'])

        # 2. 주봉으로 집계
        weekly_df = aggregate_daily_to_weekly_trading_days(daily_df, skip_latest_week=True)

        if weekly_df.empty:
            return {
                'symbol': symbol,
                'status': 'skip',
                'message': 'No weekly data generated'
            }

        # 3. 주봉 가격 데이터 저장
        price_rows = save_weekly_prices(engine, symbol, weekly_df, market)

        # 4. 주봉 지표 계산 및 저장
        indicator_rows = 0
        if pipeline is not None and saver is not None:
            indicator_df = weekly_df[['week_start', 'open', 'high', 'low', 'close', 'volume']].copy()
            indicator_df = indicator_df.rename(columns={'week_start': 'date'})
            indicator_df['date'] = pd.to_datetime(indicator_df['date'])
            indicator_df = indicator_df.set_index('date')

            outputs = pipeline.run(indicator_df)

            indicator_long_df = pipeline.to_long_dataframe(
                symbol=symbol,
                market=market,
                source='yfinance',
                outputs=outputs,
                keep_nan=True,
            )

            if not indicator_long_df.empty:
                if 'date' in indicator_long_df.columns:
                    indicator_long_df['date'] = pd.to_datetime(indicator_long_df['date']).dt.date
                indicator_long_df = indicator_long_df.rename(columns={'date': 'week_start'})
                indicator_rows = saver.save_long(indicator_long_df, mode="insert_only")

        return {
            'symbol': symbol,
            'status': 'success',
            'price_rows': price_rows,
            'indicator_rows': indicator_rows
        }

    except Exception as e:
        logger.error(f"{symbol}: Error - {e}")
        return {
            'symbol': symbol,
            'status': 'error',
            'message': str(e)
        }


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KR 지수 주봉 데이터 일괄 생성")
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
        choices=["ALL", "KOSPI", "KOSDAQ"],
        help="마켓 선택 (기본값: ALL)"
    )
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
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
            logger.info(f"사용자 지정 기간: {start_date} ~ {end_date}")
        elif args.start or args.end:
            logger.error("--start와 --end는 함께 지정하거나 둘 다 생략해야 합니다")
            return 1
        else:
            logger.info(f"기간 미지정 - {args.market} 마켓의 전체 일봉 데이터를 주봉으로 변환합니다")
            start_date, end_date = get_date_range_from_db(engine, args.market)
            logger.info(f"DB 조회 기간: {start_date} ~ {end_date}")
    except ValueError as e:
        logger.error(f"날짜 처리 오류: {e}")
        return 1

    # Load indices
    logger.info("Loading indices from kr_index_master...")
    indices = load_kr_index_symbols_with_details(engine, market=args.market)
    logger.info(f"Found {len(indices)} indices to process")

    if not indices:
        logger.warning("No indices to process")
        return 0

    # Build indicator pipeline (kr_index_weekly)
    weekly_cfg = cfg.get('indicators_kr_index_weekly', cfg.get('indicators_kr_index')) or {}
    raw_pipeline = weekly_cfg.get('pipeline') or [] if weekly_cfg else []
    pipeline_specs = [IndicatorSpec(**spec) for spec in raw_pipeline]

    if pipeline_specs:
        pipeline = IndicatorPipeline(pipeline_specs)
        table_name = weekly_cfg.get('materialization', {}).get('table_long', 'kr_index_indicators_weekly')
        saver = IndicatorSaver(engine, table_long=table_name)
    else:
        pipeline = None
        saver = None
        logger.info("No indicator pipeline configured — prices only")

    # Process all indices (sequential, only 2 indices)
    logger.info(f"Processing {len(indices)} indices from {start_date} to {end_date}...")
    success_count = 0
    skip_count = 0
    failed_results: List[Dict[str, Any]] = []

    for idx_info in indices:
        symbol = idx_info['symbol']
        name = idx_info['name']
        market = idx_info['market']

        result = process_index(symbol, name, market, start_date, end_date, pipeline, saver, engine)

        if result['status'] == 'success':
            success_count += 1
            logger.info(f"{symbol} ({name}): 가격 {result['price_rows']}건 처리(insert-only), 지표 {result['indicator_rows']}건 저장")
        elif result['status'] == 'skip':
            skip_count += 1
            logger.warning(f"{symbol} ({name}): {result.get('message', 'Skipped')}")
        else:
            failed_results.append(result)
            logger.error(f"{symbol} ({name}): {result.get('message', 'Error')}")

    # Summary
    logger.info("=" * 60)
    logger.info("KR Index Weekly Bulk Update Complete")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Skipped: {skip_count}")
    logger.info(f"  Failed:  {len(failed_results)}")
    logger.info("=" * 60)

    return 0 if not failed_results else 1


if __name__ == "__main__":
    sys.exit(main())
