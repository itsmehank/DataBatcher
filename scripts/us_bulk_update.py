#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US 주식 전체 종목 일괄 수집 스크립트

us_symbol_master 테이블의 ACTIVE 종목을 읽어 과거 데이터를 일괄 수집합니다.
병렬 처리 및 프로그레스바를 지원하며, 실패한 종목은 로그에 기록합니다.

실행 예시:
    # 전체 종목, 과거 1년치 수집
    python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --workers 4

    # NASDAQ만, 병렬 워커 8개
    python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market NASDAQ --workers 8

    # 상위 100개만
    python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --workers 4

    # 지표 계산 포함
    python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --with-indicators

주의:
    - 대량 데이터 수집이므로 시간이 오래 걸릴 수 있습니다
    - FDR rate limit을 준수하여 차단을 방지합니다
"""
from __future__ import annotations
import argparse
import sys
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.rate_limiter import RateLimiter
from core.us_symbol_loader import load_us_symbols_with_details
from collectors.us_stock import USStockCollector

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
FAILED_LOG = LOG_DIR / "us_bulk_update_failed.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def build_us_pipeline(cfg: dict) -> IndicatorPipeline:
    """US 주식용 지표 파이프라인 생성"""
    specs_cfg = cfg.get("indicators_us", {}).get("pipeline", [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    return IndicatorPipeline(specs)


def collect_single_symbol(
    symbol: str,
    name: str,
    market: str,
    start: date,
    end: date,
    collector: USStockCollector,
    pipeline: Optional[IndicatorPipeline],
    saver: Optional[IndicatorSaver],
    rate_limiter: RateLimiter
) -> Dict[str, Any]:
    """
    단일 종목 수집 및 저장

    Returns:
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market": "NASDAQ",
            "status": "success" | "error",
            "price_rows": 252,
            "indicator_rows": 504,
            "error": None | "error message"
        }
    """
    result = {
        "symbol": symbol,
        "name": name,
        "market": market,
        "status": "error",
        "price_rows": 0,
        "indicator_rows": 0,
        "error": None
    }

    try:
        # Rate limiting
        rate_limiter.acquire()

        # 1. Fetch price data
        df_price = collector.fetch(symbol, start=start, end=end, market=market)

        if df_price is None or df_price.empty:
            result["error"] = "No data returned from FDR"
            return result

        # 2. Validate
        df_price = collector.validate(df_price)

        if df_price is None or df_price.empty:
            result["error"] = "Data validation failed"
            return result

        # 3. Save prices (INSERT ONLY: preserve existing data)
        price_rows = collector.save(df_price, symbol, mode="insert_only")
        result["price_rows"] = price_rows

        # 4. Calculate indicators (if enabled)
        if pipeline and saver:
            dfp = df_price.copy()
            dfp["date"] = pd.to_datetime(dfp["date"])
            dfp.set_index("date", inplace=True)

            outputs = pipeline.run(dfp)

            if outputs:
                df_long = pipeline.to_long_dataframe(
                    symbol=symbol,
                    market=market,
                    source="fdr",
                    outputs=outputs,
                    keep_nan=True
                )

                if not df_long.empty and 'date' in df_long.columns:
                    df_long['date'] = pd.to_datetime(df_long['date']).dt.date

                    # NaN/Inf → None 변환 (MySQL 호환)
                    if 'value' in df_long.columns:
                        df_long["value"] = df_long["value"].astype("object")
                        df_long.loc[~np.isfinite(pd.to_numeric(df_long["value"], errors="coerce")), "value"] = None

                # INSERT ONLY: preserve existing indicators
                indicator_rows = saver.save_long(df_long, mode="insert_only")
                result["indicator_rows"] = indicator_rows

        result["status"] = "success"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to collect {symbol} ({name}): {e}")

    return result


def parallel_collect(
    symbols: List[dict],
    start: date,
    end: date,
    workers: int,
    cfg: Dict,
    engine: Engine,
    with_indicators: bool
) -> List[Dict[str, Any]]:
    """
    병렬 처리로 전체 종목 수집
    """
    # Rate limiter 초기화
    rate_limit = cfg.get("runtime", {}).get("rate_limit_per_sec", 5.0)
    rate_limiter = RateLimiter(rate_limit)

    # Collector 준비
    collector = USStockCollector(engine)

    # Pipeline, saver 준비 (지표 계산 시에만)
    pipeline = None
    saver = None
    if with_indicators:
        pipeline = build_us_pipeline(cfg)
        table_long = cfg.get("indicators_us", {}).get("materialization", {}).get("table_long", "us_stock_indicators")
        saver = IndicatorSaver(engine, table_long=table_long)

    results = []

    logger.info(f"Starting US bulk collection with {workers} workers, rate limit: {rate_limit} req/sec")
    if with_indicators:
        logger.info("Indicator calculation enabled")

    # ThreadPoolExecutor + tqdm progress bar
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                collect_single_symbol,
                sym_info["symbol"], sym_info["name"], sym_info["market"],
                start, end, collector, pipeline, saver, rate_limiter
            ): sym_info
            for sym_info in symbols
        }

        # Progress bar
        with tqdm(total=len(symbols), desc="Collecting", unit="symbol") as pbar:
            for future in as_completed(futures):
                sym_info = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Update progress bar description
                    if result["status"] == "success":
                        pbar.set_postfix_str(f"✓ {sym_info['symbol']}")
                    else:
                        pbar.set_postfix_str(f"✗ {sym_info['symbol']}")

                except Exception as e:
                    logger.error(f"Unexpected error for {sym_info['symbol']}: {e}")
                    results.append({
                        "symbol": sym_info["symbol"],
                        "name": sym_info["name"],
                        "market": sym_info["market"],
                        "status": "error",
                        "price_rows": 0,
                        "indicator_rows": 0,
                        "error": f"Unexpected: {e}"
                    })

                pbar.update(1)

    return results


def write_failed_log(failed_results: List[Dict[str, Any]]) -> None:
    """실패한 종목을 로그 파일에 기록"""
    if not failed_results:
        return

    with open(FAILED_LOG, "w", encoding="utf-8") as f:
        f.write(f"# US Bulk Update Failed Symbols - {datetime.now()}\n")
        f.write(f"# Total failed: {len(failed_results)}\n\n")

        for res in failed_results:
            f.write(f"{res['symbol']}\t{res['name']}\t{res['market']}\t{res['error']}\n")

    logger.info(f"Failed symbols logged to: {FAILED_LOG}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="US 주식 전체 종목 일괄 수집 (Bulk Update)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 전체 종목, 과거 1년치
  python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31

  # NASDAQ만, 병렬 8개
  python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --market NASDAQ --workers 8

  # 상위 100개 + 지표 계산
  python scripts/us_bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100 --with-indicators
        """
    )

    p.add_argument("--start", required=True, help="수집 시작일 (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="수집 종료일 (YYYY-MM-DD)")
    p.add_argument("--market", choices=["NYSE", "NASDAQ", "ETF", "ALL"],
                   default="ALL", help="수집할 마켓 (default: ALL)")
    p.add_argument("--top", type=int, default=None,
                   help="상위 N개만 수집 (default: 전체)")
    p.add_argument("--workers", type=int, default=4,
                   help="병렬 워커 수 (default: 4)")
    p.add_argument("--with-indicators", action="store_true",
                   help="지표 계산 포함")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    start_time = datetime.now()

    try:
        # Parse dates
        start_date = pd.to_datetime(args.start).date()
        end_date = pd.to_datetime(args.end).date()

        logger.info("="*60)
        logger.info("US Stock Bulk Update")
        logger.info("="*60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Market: {args.market}")
        logger.info(f"Top: {args.top if args.top else 'All'}")
        logger.info(f"Workers: {args.workers}")
        logger.info(f"With Indicators: {args.with_indicators}")
        logger.info("="*60)

        # Load config and init DB
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # Load symbols
        logger.info("Loading symbols from us_symbol_master...")
        symbols = load_us_symbols_with_details(engine, market=args.market, top=args.top)

        if not symbols:
            logger.error("No ACTIVE symbols found in us_symbol_master. Run us_sync_symbol_master.py first.")
            sys.exit(1)

        logger.info(f"Loaded {len(symbols)} ACTIVE symbols")

        # Parallel collect
        results = parallel_collect(
            symbols, start_date, end_date, args.workers, cfg, engine, args.with_indicators
        )

        # Analyze results
        success_results = [r for r in results if r["status"] == "success"]
        failed_results = [r for r in results if r["status"] == "error"]

        total_price_rows = sum(r["price_rows"] for r in success_results)
        total_indicator_rows = sum(r["indicator_rows"] for r in success_results)

        # Write failed log
        if failed_results:
            write_failed_log(failed_results)

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("="*60)
        logger.info("Summary")
        logger.info("="*60)
        logger.info(f"Success: {len(success_results)} symbols")
        logger.info(f"Failed: {len(failed_results)} symbols")
        logger.info(f"Total price rows: {total_price_rows:,}")
        logger.info(f"Total indicator rows: {total_indicator_rows:,}")
        logger.info(f"Duration: {elapsed/60:.1f} minutes")
        logger.info("="*60)

        if failed_results:
            logger.warning(f"⚠️  {len(failed_results)} symbols failed. See: {FAILED_LOG}")
        else:
            logger.info("✅ All symbols collected successfully!")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
