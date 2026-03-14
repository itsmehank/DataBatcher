#!/usr/bin/env python3
"""
전체 종목 일괄 수집 스크립트

symbol_master 테이블의 ACTIVE 종목을 읽어 과거 데이터를 일괄 수집합니다.
병렬 처리 및 프로그레스바를 지원하며, 실패한 종목은 로그에 기록합니다.

실행 예시:
    # 전체 종목, 과거 5년치 수집
    python scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31

    # KOSPI만, 병렬 워커 8개
    python scripts/bulk_update.py --start 2023-01-01 --end 2024-12-31 --market KOSPI --workers 8

    # 심볼 정렬 기준 상위 100개만
    python scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100

주의:
    - 대량 데이터 수집이므로 시간이 오래 걸릴 수 있습니다 (전체 종목 10-20분)
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
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.rate_limiter import RateLimiter
from collectors.kr_stock import KRStockCollector
from collectors.kr_etf import KREtfCollector

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
FAILED_LOG = LOG_DIR / "bulk_update_failed.log"

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
    DB에서 수집 대상 종목 목록 로드

    Args:
        engine: SQLAlchemy engine
        market: KOSPI/KOSDAQ/KONEX/ALL (default: ALL)
        top: 심볼 정렬 기준 상위 N개만 (default: None = 전체)

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

    sql += " ORDER BY symbol"  # Consistent ordering

    if top:
        sql += " LIMIT :top"
        params["top"] = int(top)

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.all()

    return [(row[0], row[1], row[2]) for row in rows]


def collect_single_symbol(
    symbol: str,
    name: str,
    market: str,
    start: date,
    end: date,
    stock_collector: KRStockCollector,
    etf_collector: KREtfCollector,
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    rate_limiter: RateLimiter
) -> Dict[str, Any]:
    """
    단일 종목 수집 및 저장

    Args:
        symbol: 종목코드
        name: 종목명
        market: 마켓
        start: 시작일
        end: 종료일
        stock_collector: KRStockCollector 인스턴스
        etf_collector: KREtfCollector 인스턴스
        pipeline: IndicatorPipeline 인스턴스
        saver: IndicatorSaver 인스턴스
        rate_limiter: RateLimiter 인스턴스

    Returns:
        {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
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
        collector = etf_collector if market == "ETF" else stock_collector
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

        # 4. Calculate indicators
        dfp = df_price.copy()
        dfp["date"] = pd.to_datetime(dfp["date"])
        dfp.set_index("date", inplace=True)

        outputs = pipeline.run(dfp)

        if outputs:
            df_long = pipeline.to_long_dataframe(
                symbol=symbol,
                market=market,
                source="pykrx",
                outputs=outputs,
                keep_nan=True,
            )
            # date 컬럼을 date 타입으로 변환 (yyyy-mm-dd 형식)
            if not df_long.empty and 'date' in df_long.columns:
                df_long['date'] = pd.to_datetime(df_long['date']).dt.date
            # INSERT ONLY: preserve existing indicators
            indicator_rows = saver.save_long(df_long, mode="insert_only")
            result["indicator_rows"] = indicator_rows

        result["status"] = "success"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to collect {symbol} ({name}): {e}")

    return result


def parallel_collect(
    symbols: List[Tuple[str, str, str]],
    start: date,
    end: date,
    workers: int,
    cfg: Dict,
    engine: Engine
) -> List[Dict[str, Any]]:
    """
    병렬 처리로 전체 종목 수집

    Args:
        symbols: [(symbol, name, market), ...]
        start: 시작일
        end: 종료일
        workers: 병렬 워커 수
        cfg: 설정 dict
        engine: SQLAlchemy engine

    Returns:
        [결과 dict, ...]
    """
    # Rate limiter 초기화
    rate_limit = cfg.get("runtime", {}).get("rate_limit_per_sec", 5.0)
    rate_limiter = RateLimiter(rate_limit)

    # Collector, pipeline, saver 준비 (각 워커가 공유)
    stock_collector = KRStockCollector(engine)
    etf_collector = KREtfCollector(engine)

    specs_cfg = cfg.get("indicators", {}).get("pipeline", [])
    specs = [IndicatorSpec(**x) for x in specs_cfg]
    pipeline = IndicatorPipeline(specs)

    table_long = cfg.get("indicators", {}).get("materialization", {}).get("table_long", "stock_indicators")
    saver = IndicatorSaver(engine, table_long=table_long)

    results = []

    logger.info(f"Starting bulk collection with {workers} workers, rate limit: {rate_limit} req/sec")

    # ThreadPoolExecutor + tqdm progress bar
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                collect_single_symbol,
                symbol, name, market, start, end,
                stock_collector, etf_collector, pipeline, saver, rate_limiter
            ): (symbol, name, market)
            for symbol, name, market in symbols
        }

        # Progress bar
        with tqdm(total=len(symbols), desc="Collecting", unit="symbol") as pbar:
            for future in as_completed(futures):
                symbol, name, market = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Update progress bar description
                    if result["status"] == "success":
                        pbar.set_postfix_str(f"✓ {symbol}")
                    else:
                        pbar.set_postfix_str(f"✗ {symbol}")

                except Exception as e:
                    logger.error(f"Unexpected error for {symbol}: {e}")
                    results.append({
                        "symbol": symbol,
                        "name": name,
                        "market": market,
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
        f.write(f"# Bulk Update Failed Symbols - {datetime.now()}\n")
        f.write(f"# Total failed: {len(failed_results)}\n\n")

        for res in failed_results:
            f.write(f"{res['symbol']}\t{res['name']}\t{res['market']}\t{res['error']}\n")

    logger.info(f"Failed symbols logged to: {FAILED_LOG}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="전체 종목 일괄 수집 (Bulk Update)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 전체 종목, 과거 5년치
  python scripts/bulk_update.py --start 2020-01-01 --end 2024-12-31

  # KOSPI만, 병렬 8개
  python scripts/bulk_update.py --start 2023-01-01 --end 2024-12-31 --market KOSPI --workers 8

  # 심볼 정렬 기준 상위 100개
  python scripts/bulk_update.py --start 2024-01-01 --end 2024-12-31 --top 100
        """
    )

    p.add_argument("--start", required=True, help="수집 시작일 (YYYY-MM-DD)")
    p.add_argument("--end", required=True, help="수집 종료일 (YYYY-MM-DD)")
    p.add_argument("--market", choices=["KOSPI", "KOSDAQ", "KONEX", "ETF", "ALL"],
                   default="ALL", help="수집할 마켓 (default: ALL)")
    p.add_argument("--top", type=int, default=None,
                   help="심볼 정렬 기준 상위 N개만 수집 (default: 전체)")
    p.add_argument("--workers", type=int, default=4,
                   help="병렬 워커 수 (default: 4)")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    start_time = datetime.now()

    try:
        # Parse dates
        start_date = pd.to_datetime(args.start).date()
        end_date = pd.to_datetime(args.end).date()

        logger.info("="*60)
        logger.info("DataBatcher Bulk Update")
        logger.info("="*60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Market: {args.market}")
        logger.info(f"Top: {args.top if args.top else 'All'}")
        logger.info(f"Workers: {args.workers}")
        logger.info("="*60)

        # Load config and init DB
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # Load symbols
        logger.info("Loading symbols from symbol_master...")
        symbols = load_symbols(engine, market=args.market, top=args.top)

        if not symbols:
            logger.error("No ACTIVE symbols found in symbol_master. Run sync_symbol_master.py first.")
            sys.exit(1)

        logger.info(f"Loaded {len(symbols)} ACTIVE symbols")

        # Parallel collect
        results = parallel_collect(symbols, start_date, end_date, args.workers, cfg, engine)

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
