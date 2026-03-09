#!/usr/bin/env python3
"""
KR 지수 과거 데이터 일괄 수집 스크립트

kr_index_master의 ACTIVE 지수를 읽어 과거 OHLCV 데이터를 일괄 수집합니다.
지수는 2개뿐이므로 병렬 처리 없이 순차 처리합니다.

실행 예시:
    python scripts/kr_index_bulk_update.py --start 2020-01-01 --end 2024-12-31
    python scripts/kr_index_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market KOSPI
"""
from __future__ import annotations
import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.kr_index_symbol_loader import load_kr_index_symbols_with_details
from collectors.kr_index import KRIndexCollector

# Import indicator modules to register them
from indicators.common import sma as _reg_sma  # noqa: F401
from indicators.common import ema as _reg_ema  # noqa: F401

from indicators.pipeline import IndicatorPipeline, IndicatorSpec
from savers.indicator_saver import IndicatorSaver

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def build_pipeline(cfg) -> IndicatorPipeline:
    specs_cfg = cfg.get("indicators_kr_index", {}).get("pipeline", [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def collect_single_index(
    symbol: str,
    name: str,
    market: str,
    start,
    end,
    collector: KRIndexCollector,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
) -> dict:
    """단일 지수 수집 및 저장"""
    result = {
        "symbol": symbol,
        "name": name,
        "market": market,
        "status": "error",
        "price_rows": 0,
        "indicator_rows": 0,
        "error": None,
    }

    try:
        # 1. Fetch price data
        df_price = collector.fetch(symbol, start=start, end=end, market=market)

        if df_price is None or df_price.empty:
            result["error"] = "No data returned from yfinance"
            return result

        # 2. Validate
        df_price = collector.validate(df_price)

        if df_price is None or df_price.empty:
            result["error"] = "Data validation failed"
            return result

        # 3. Save prices (INSERT ONLY)
        price_rows = collector.save(df_price, symbol, mode="insert_only")
        result["price_rows"] = price_rows

        # 4. Calculate indicators
        dfp = df_price.copy()
        dfp["date"] = pd.to_datetime(dfp["date"])
        dfp.set_index("date", inplace=True)

        outputs = pipeline.run(dfp)

        if outputs:
            df_long = pipeline.to_long_dataframe(
                symbol=symbol,
                market=market,
                source="yfinance",
                outputs=outputs,
                keep_nan=True,
            )
            if not df_long.empty and 'date' in df_long.columns:
                df_long['date'] = pd.to_datetime(df_long['date']).dt.date
            # INSERT ONLY
            indicator_rows = saver.save_long(df_long, mode="insert_only")
            result["indicator_rows"] = indicator_rows

        result["status"] = "success"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to collect {symbol} ({name}): {e}")

    return result


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="KR 지수 과거 데이터 일괄 수집 (Bulk Update)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/kr_index_bulk_update.py --start 2020-01-01 --end 2024-12-31
  python scripts/kr_index_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market KOSPI
        """
    )

    p.add_argument("--start", required=True, help="수집 시작일 (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="수집 종료일 (YYYY-MM-DD)")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "ALL"],
                   default="ALL", help="수집할 마켓 (default: ALL)")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    start_time = datetime.now()

    try:
        start_date = pd.to_datetime(args.start).date()
        end_date = pd.to_datetime(args.end).date()

        logger.info("=" * 60)
        logger.info("DataBatcher KR Index Bulk Update")
        logger.info("=" * 60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Market: {args.market}")
        logger.info("=" * 60)

        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # Load indices
        indices = load_kr_index_symbols_with_details(engine, market=args.market)

        if not indices:
            logger.error("No ACTIVE indices found in kr_index_master. Run kr_index_sync_master.py first.")
            sys.exit(1)

        logger.info(f"Loaded {len(indices)} ACTIVE indices")

        # Prepare components
        collector = KRIndexCollector(engine)
        pipeline = build_pipeline(cfg)
        table_long = cfg.get("indicators_kr_index", {}).get("materialization", {}).get("table_long", "kr_index_indicators")
        saver = IndicatorSaver(engine, table_long=table_long)

        # Collect each index (sequential, only 2 indices)
        results = []
        for idx_info in indices:
            symbol = idx_info["symbol"]
            name = idx_info["name"]
            market = idx_info["market"]

            logger.info(f"Collecting {symbol} ({name}) [{market}]...")
            result = collect_single_index(
                symbol, name, market,
                start_date, end_date,
                collector, pipeline, saver,
            )
            results.append(result)

            if result["status"] == "success":
                logger.info(f"  Prices: {result['price_rows']} rows, Indicators: {result['indicator_rows']} rows")
            else:
                logger.error(f"  Failed: {result['error']}")

        # Summary
        success_results = [r for r in results if r["status"] == "success"]
        failed_results = [r for r in results if r["status"] == "error"]

        total_price_rows = sum(r["price_rows"] for r in success_results)
        total_indicator_rows = sum(r["indicator_rows"] for r in success_results)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info(f"Success: {len(success_results)} indices")
        logger.info(f"Failed: {len(failed_results)} indices")
        logger.info(f"Total price rows: {total_price_rows:,}")
        logger.info(f"Total indicator rows: {total_indicator_rows:,}")
        logger.info(f"Duration: {elapsed:.1f}s")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
