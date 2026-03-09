#!/usr/bin/env python3
"""
독립 지표 백필 스크립트

DB에 이미 적재된 가격 데이터(stock_prices / us_stock_prices)로부터
지표만 별도로 계산하여 적재합니다.

가격 수집 없이 지표만 재계산할 수 있어, 새 지표 추가 시
기존 파이프라인(daily_update, bulk_update)을 재실행할 필요가 없습니다.

지원 범위:
  - @IndicatorRegistry.register 기반 per-symbol 지표 (SMA, EMA 등)
  - RS Rating/RS Line/Blue Dot 같은 cross-sectional 지표는 별도 스크립트 사용

실행 예시:
    # 한국 주식 전체
    python scripts/backfill_indicators.py --source stock_prices

    # 미국 주식, NASDAQ만
    python scripts/backfill_indicators.py --source us_stock_prices --market NASDAQ

    # 특정 종목만
    python scripts/backfill_indicators.py --source stock_prices --symbols 005930 000660

    # upsert 모드 (기존 지표 덮어쓰기)
    python scripts/backfill_indicators.py --source stock_prices --mode upsert

    # 병렬 워커 수 지정
    python scripts/backfill_indicators.py --source us_stock_prices --workers 8
"""
from __future__ import annotations
import argparse
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.price_loader import load_price_data
from core.symbol_loader import load_symbols_with_details
from core.us_symbol_loader import load_us_symbols_with_details

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
FAILED_LOG = LOG_DIR / "backfill_indicators_failed.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Source configuration mapping
SOURCE_MAP = {
    "stock_prices": {
        "price_table": "stock_prices",
        "indicator_table": "stock_indicators",
        "config_key": "indicators_backfill",
        "symbol_loader": "kr",
        "default_source": "pykrx",
        "price_columns": ["date", "open", "high", "low", "close", "adj_close", "volume"],
    },
    "us_stock_prices": {
        "price_table": "us_stock_prices",
        "indicator_table": "us_stock_indicators",
        "config_key": "indicators_us_backfill",
        "symbol_loader": "us",
        "default_source": "fdr",
        "price_columns": ["date", "open", "high", "low", "close", "adj_close", "volume"],
    },
}


def get_date_range(engine: Engine, symbol: str, price_table: str):
    """Get MIN and MAX date for a symbol from the price table."""
    sql = text(f"""
        SELECT MIN(date) AS min_date, MAX(date) AS max_date
        FROM `{price_table}`
        WHERE symbol = :symbol
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"symbol": symbol}).mappings().first()
        if row and row["min_date"] and row["max_date"]:
            return row["min_date"], row["max_date"]
    return None, None


def process_symbol(
    symbol: str,
    name: str,
    market: str,
    engine: Engine,
    source_cfg: Dict[str, Any],
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    warmup_days: int,
    mode: str,
) -> Dict[str, Any]:
    """
    단일 종목의 지표를 백필합니다.

    1. DB에서 해당 종목의 날짜 범위 조회
    2. warmup 포함 가격 데이터 로드
    3. 지표 계산
    4. long-form 변환 후 DB 저장
    """
    result = {
        "symbol": symbol,
        "name": name,
        "market": market,
        "status": "error",
        "indicator_rows": 0,
        "error": None,
    }

    try:
        price_table = source_cfg["price_table"]

        # 1. Get date range for this symbol
        min_date, max_date = get_date_range(engine, symbol, price_table)
        if min_date is None:
            result["error"] = "No price data in DB"
            return result

        # 2. Load price data with warmup
        warmup_start = min_date - timedelta(days=warmup_days + 30)  # extra margin for holidays
        df = load_price_data(
            engine, symbol, warmup_start, max_date,
            table=price_table,
            columns=source_cfg["price_columns"],
        )

        if df.empty:
            result["error"] = "Empty price data from DB"
            return result

        # 3. Calculate indicators
        dfp = df.copy()
        dfp["date"] = pd.to_datetime(dfp["date"])
        dfp.set_index("date", inplace=True)

        outputs = pipeline.run(dfp)

        if not outputs:
            result["error"] = "No indicator outputs"
            return result

        # 4. Convert to long-form and save
        df_long = pipeline.to_long_dataframe(
            symbol=symbol,
            market=market,
            source=source_cfg["default_source"],
            outputs=outputs,
            keep_nan=False,
        )

        if df_long.empty:
            result["status"] = "success"
            return result

        # Convert date column to date type
        df_long["date"] = pd.to_datetime(df_long["date"]).dt.date

        indicator_rows = saver.save_long(df_long, mode=mode)
        result["indicator_rows"] = indicator_rows
        result["status"] = "success"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to backfill {symbol} ({name}): {e}")

    return result


def load_symbol_list(
    engine: Engine,
    source_cfg: Dict[str, Any],
    market: Optional[str] = None,
    symbols: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Load symbol list based on source type."""
    if symbols:
        # --symbols takes priority: return as-is with minimal info
        return [{"symbol": s, "name": s, "market": market or "UNKNOWN"} for s in symbols]

    loader = source_cfg["symbol_loader"]
    if loader == "kr":
        return load_symbols_with_details(engine, market=market or "ALL")
    elif loader == "us":
        return load_us_symbols_with_details(engine, market=market or "ALL")
    else:
        raise ValueError(f"Unknown symbol_loader: {loader}")


def parallel_backfill(
    symbol_list: List[Dict[str, Any]],
    workers: int,
    engine: Engine,
    source_cfg: Dict[str, Any],
    pipeline: IndicatorPipeline,
    saver: IndicatorSaver,
    warmup_days: int,
    mode: str,
) -> List[Dict[str, Any]]:
    """병렬 처리로 전체 종목 지표 백필."""
    results = []

    logger.info(f"Starting backfill with {workers} workers, mode={mode}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                process_symbol,
                sym["symbol"], sym["name"], sym["market"],
                engine, source_cfg, pipeline, saver, warmup_days, mode,
            ): sym
            for sym in symbol_list
        }

        with tqdm(total=len(symbol_list), desc="Backfilling", unit="symbol") as pbar:
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    res = future.result()
                    results.append(res)
                    if res["status"] == "success":
                        pbar.set_postfix_str(f"ok {sym['symbol']}")
                    else:
                        pbar.set_postfix_str(f"err {sym['symbol']}")
                except Exception as e:
                    logger.error(f"Unexpected error for {sym['symbol']}: {e}")
                    results.append({
                        "symbol": sym["symbol"],
                        "name": sym["name"],
                        "market": sym["market"],
                        "status": "error",
                        "indicator_rows": 0,
                        "error": f"Unexpected: {e}",
                    })
                pbar.update(1)

    return results


def write_failed_log(failed_results: List[Dict[str, Any]]) -> None:
    """실패한 종목을 로그 파일에 기록."""
    if not failed_results:
        return
    with open(FAILED_LOG, "w", encoding="utf-8") as f:
        f.write(f"# Backfill Indicators Failed Symbols - {datetime.now()}\n")
        f.write(f"# Total failed: {len(failed_results)}\n\n")
        for res in failed_results:
            f.write(f"{res['symbol']}\t{res['name']}\t{res['market']}\t{res['error']}\n")
    logger.info(f"Failed symbols logged to: {FAILED_LOG}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="독립 지표 백필 (DB 가격 데이터 → 지표 계산/적재)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 한국 주식 전체
  python scripts/backfill_indicators.py --source stock_prices

  # 미국 주식, NASDAQ만
  python scripts/backfill_indicators.py --source us_stock_prices --market NASDAQ

  # 특정 종목만
  python scripts/backfill_indicators.py --source stock_prices --symbols 005930 000660

  # 기존 지표 덮어쓰기
  python scripts/backfill_indicators.py --source stock_prices --mode upsert
        """,
    )
    p.add_argument(
        "--source", required=True,
        choices=list(SOURCE_MAP.keys()),
        help="가격 데이터 소스 테이블 (stock_prices / us_stock_prices)",
    )
    p.add_argument(
        "--market", default=None,
        help="시장 필터 (KR: KOSPI/KOSDAQ/KONEX/ETF/ALL, US: NYSE/NASDAQ/ETF/ALL)",
    )
    p.add_argument(
        "--symbols", nargs="+", default=None,
        help="종목 코드 목록 (--market보다 우선)",
    )
    p.add_argument(
        "--workers", type=int, default=4,
        help="병렬 워커 수 (default: 4)",
    )
    p.add_argument(
        "--mode", choices=["insert_only", "upsert"], default="insert_only",
        help="저장 모드 (default: insert_only)",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    start_time = datetime.now()

    try:
        source_cfg = SOURCE_MAP[args.source]

        logger.info("=" * 60)
        logger.info("DataBatcher Indicator Backfill")
        logger.info("=" * 60)
        logger.info(f"Source: {args.source}")
        logger.info(f"Config key: {source_cfg['config_key']}")
        logger.info(f"Market: {args.market or 'ALL'}")
        logger.info(f"Symbols: {args.symbols or 'all from master'}")
        logger.info(f"Workers: {args.workers}")
        logger.info(f"Mode: {args.mode}")
        logger.info("=" * 60)

        # Load config and init DB
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # Load indicator pipeline from config
        config_key = source_cfg["config_key"]
        ind_cfg = cfg.get(config_key, {})
        if not ind_cfg:
            logger.error(
                f"Config section '{config_key}' not found in settings.yaml. "
                f"Please add it before running backfill."
            )
            sys.exit(1)

        specs_cfg = ind_cfg.get("pipeline", [])
        if not specs_cfg:
            logger.error(f"No indicators defined in '{config_key}.pipeline'.")
            sys.exit(1)

        specs = [IndicatorSpec(**x) for x in specs_cfg]
        pipeline = IndicatorPipeline(specs)
        warmup_days = pipeline.warmup_days()

        indicator_table = ind_cfg.get("materialization", {}).get(
            "table_long", source_cfg["indicator_table"]
        )
        saver = IndicatorSaver(engine, table_long=indicator_table)

        logger.info(f"Pipeline: {len(specs)} indicators, warmup={warmup_days} days")
        logger.info(f"Target table: {indicator_table}")

        # Load symbols
        symbol_list = load_symbol_list(engine, source_cfg, market=args.market, symbols=args.symbols)

        if not symbol_list:
            logger.error("No symbols found. Check symbol_master or --symbols argument.")
            sys.exit(1)

        logger.info(f"Loaded {len(symbol_list)} symbols")

        # Run backfill
        results = parallel_backfill(
            symbol_list, args.workers, engine,
            source_cfg, pipeline, saver, warmup_days, args.mode,
        )

        # Analyze results
        success_results = [r for r in results if r["status"] == "success"]
        failed_results = [r for r in results if r["status"] == "error"]
        total_indicator_rows = sum(r["indicator_rows"] for r in success_results)

        if failed_results:
            write_failed_log(failed_results)

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info(f"Success: {len(success_results)} symbols")
        logger.info(f"Failed: {len(failed_results)} symbols")
        logger.info(f"Total indicator rows: {total_indicator_rows:,}")
        logger.info(f"Duration: {elapsed / 60:.1f} minutes")
        logger.info("=" * 60)

        if failed_results:
            logger.warning(f"{len(failed_results)} symbols failed. See: {FAILED_LOG}")
        else:
            logger.info("All symbols backfilled successfully!")

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
