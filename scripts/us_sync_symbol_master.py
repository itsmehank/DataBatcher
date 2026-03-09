#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US 종목 마스터 동기화 스크립트 (FinanceDataReader 기반)

FDR을 사용하여 NYSE, NASDAQ, ETF 종목 목록을 가져와 us_symbol_master 테이블에 동기화합니다.

주요 기능:
- 신규 상장 종목 추가 (status=ACTIVE)
- 기존 종목 정보 업데이트 (name 등 메타데이터)
- 상장폐지 종목 상태 변경 (status=DELISTED)

실행:
    python scripts/us_sync_symbol_master.py
    python scripts/us_sync_symbol_master.py --market NYSE

주기:
    주 1회 실행 권장 (신규 상장/상장폐지 종목 감지용)
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Set

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig

try:
    import FinanceDataReader as fdr
except ImportError:
    print("Error: FinanceDataReader not installed. Run: pip install finance-datareader", file=sys.stderr)
    sys.exit(1)


def fetch_us_listing(market: str) -> pd.DataFrame:
    """
    FDR에서 US 종목 목록 가져오기

    Args:
        market: NYSE, NASDAQ, ETF/US

    Returns:
        DataFrame with columns:
        - symbol: 종목코드 (str)
        - Name: 종목명 (str)
        - Market: NYSE/NASDAQ/ETF (str)
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching {market} listing from FDR...")

    try:
        df = fdr.StockListing(market)

        if df is None or df.empty:
            print(f"  -> {market}: No data returned")
            return pd.DataFrame()

        # 컬럼명 확인 및 정규화
        # FDR은 보통 Symbol, Name 컬럼을 반환
        if 'Symbol' in df.columns:
            df = df.rename(columns={'Symbol': 'symbol'})
        elif 'symbol' not in df.columns:
            # 첫 번째 컬럼을 symbol로 가정
            df = df.rename(columns={df.columns[0]: 'symbol'})

        # Name 컬럼 확인
        if 'Name' not in df.columns:
            # name 소문자 확인
            if 'name' in df.columns:
                df = df.rename(columns={'name': 'Name'})
            else:
                df['Name'] = ''

        # Market 컬럼 추가/정규화
        if market == 'ETF/US':
            df['Market'] = 'ETF'
        else:
            df['Market'] = market

        # Industry 컬럼 보존 (NYSE/NASDAQ에 존재, ETF에는 없을 수 있음)
        if 'Industry' not in df.columns:
            if 'industry' in df.columns:
                df = df.rename(columns={'industry': 'Industry'})
            else:
                df['Industry'] = None

        # symbol_type 할당
        if market == 'ETF/US':
            df['symbol_type'] = 'ETF'
        else:
            df['symbol_type'] = 'STOCK'

        print(f"  -> {market}: {len(df)} symbols")
        return df[['symbol', 'Name', 'Market', 'Industry', 'symbol_type']]

    except Exception as e:
        print(f"  -> {market}: Error - {e}", file=sys.stderr)
        return pd.DataFrame()


def load_existing_symbols(engine: Engine) -> Dict[str, Dict]:
    """
    DB에서 기존 종목 목록 로드

    Returns:
        {symbol: {name, market, status}, ...}
    """
    sql = text("""
        SELECT symbol, name, market, status
        FROM us_symbol_master
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)
        rows = result.mappings().all()

    return {
        row['symbol']: {
            'name': row['name'],
            'market': row['market'],
            'status': row['status']
        }
        for row in rows
    }


def compare_and_classify(
    fdr_df: pd.DataFrame,
    existing_symbols: Dict[str, Dict]
) -> Tuple[pd.DataFrame, pd.DataFrame, Set[str]]:
    """
    FDR 종목과 DB 종목을 비교하여 분류

    Returns:
        (신규종목 DataFrame, 업데이트종목 DataFrame, 상장폐지종목 set)
    """
    fdr_symbols = set(fdr_df['symbol'].tolist())
    db_symbols = set(existing_symbols.keys())

    # 신규 종목: FDR에는 있지만 DB에 없음
    new_symbols = fdr_symbols - db_symbols
    new_df = fdr_df[fdr_df['symbol'].isin(new_symbols)].copy()

    # 업데이트 종목: 둘 다 있음
    update_symbols = fdr_symbols & db_symbols
    update_df = fdr_df[fdr_df['symbol'].isin(update_symbols)].copy()

    # 상장폐지 종목: DB에는 있지만 FDR에 없음 (단, 이미 DELISTED가 아닌 것만)
    delisted_symbols = {
        s for s in (db_symbols - fdr_symbols)
        if existing_symbols[s]['status'] != 'DELISTED'
    }

    return new_df, update_df, delisted_symbols


def upsert_us_symbol_master(
    engine: Engine,
    new_symbols: pd.DataFrame,
    update_symbols: pd.DataFrame,
    delisted_symbols: Set[str]
) -> Dict[str, int]:
    """
    us_symbol_master 테이블 업데이트

    Returns:
        {"added": N, "updated": N, "delisted": N}
    """
    stats = {"added": 0, "updated": 0, "delisted": 0}

    def _val(row, col):
        """Get value from row, converting NaN to None for MySQL compatibility."""
        v = row.get(col)
        if pd.isna(v):
            return None
        return v

    with engine.begin() as conn:
        # 1. 신규 종목 추가
        if not new_symbols.empty:
            insert_sql = text("""
                INSERT INTO us_symbol_master
                  (symbol, market, symbol_type, name, status,
                   sector, industry, sector_source, sector_updated_at,
                   etl_loaded_at, updated_at)
                VALUES
                  (:symbol, :market, :symbol_type, :name, 'ACTIVE',
                   :sector, :industry, :sector_source,
                   CASE WHEN :sector IS NOT NULL OR :industry IS NOT NULL THEN NOW() ELSE NULL END,
                   NOW(), NOW())
            """)

            for _, row in new_symbols.iterrows():
                industry = _val(row, 'Industry')
                conn.execute(insert_sql, {
                    'symbol': row['symbol'],
                    'market': row['Market'],
                    'symbol_type': _val(row, 'symbol_type'),
                    'name': row['Name'],
                    'sector': _val(row, 'sector'),
                    'industry': industry,
                    'sector_source': 'fdr' if industry else None,
                })
                stats['added'] += 1

        # 2. 기존 종목 업데이트 (COALESCE preserves existing sector/industry if new is NULL)
        if not update_symbols.empty:
            update_sql = text("""
                UPDATE us_symbol_master
                SET name = :name,
                    market = :market,
                    symbol_type = :symbol_type,
                    status = 'ACTIVE',
                    sector = COALESCE(:sector, sector),
                    industry = COALESCE(:industry, industry),
                    sector_source = CASE
                        WHEN :sector_source IS NOT NULL AND sector_source IS NOT NULL
                             AND sector_source != :sector_source
                             AND sector_source NOT LIKE CONCAT('%', :sector_source, '%')
                        THEN CONCAT(sector_source, '+', :sector_source)
                        WHEN :sector_source IS NOT NULL
                        THEN COALESCE(sector_source, :sector_source)
                        ELSE sector_source
                    END,
                    sector_updated_at = CASE
                        WHEN :sector IS NOT NULL OR :industry IS NOT NULL THEN NOW()
                        ELSE sector_updated_at
                    END,
                    updated_at = NOW()
                WHERE symbol = :symbol
            """)

            for _, row in update_symbols.iterrows():
                industry = _val(row, 'Industry')
                conn.execute(update_sql, {
                    'symbol': row['symbol'],
                    'market': row['Market'],
                    'symbol_type': _val(row, 'symbol_type'),
                    'name': row['Name'],
                    'sector': _val(row, 'sector'),
                    'industry': industry,
                    'sector_source': 'fdr' if industry else None,
                })
                stats['updated'] += 1

        # 3. 상장폐지 종목 상태 변경
        if delisted_symbols:
            delist_sql = text("""
                UPDATE us_symbol_master
                SET status = 'DELISTED',
                    updated_at = NOW()
                WHERE symbol = :symbol
            """)

            for symbol in delisted_symbols:
                conn.execute(delist_sql, {'symbol': symbol})
                stats['delisted'] += 1

    return stats


def enrich_sectors_yfinance(engine: Engine, rate_limit: float = 2.0,
                            yfinance_limit: int = 0) -> Dict[str, int]:
    """
    yfinance를 사용하여 sector가 NULL인 STOCK 종목의 sector를 보완

    Args:
        engine: SQLAlchemy engine
        rate_limit: 초당 요청 수 (기본 2.0)
        yfinance_limit: 최대 호출 수 제한 (0=무제한)

    Returns:
        {"enriched": N, "failed": N, "skipped": N}
    """
    try:
        import yfinance as yf
    except ImportError:
        print("  Warning: yfinance not installed. Skipping sector enrichment.")
        print("  Install with: pip install yfinance")
        return {"enriched": 0, "failed": 0, "skipped": 0}

    from core.rate_limiter import RateLimiter

    # DB에서 sector가 NULL인 STOCK 종목만 대상
    sql = text("""
        SELECT symbol FROM us_symbol_master
        WHERE status = 'ACTIVE'
          AND (symbol_type = 'STOCK' OR symbol_type IS NULL)
          AND sector IS NULL
        ORDER BY symbol
    """)

    with engine.connect() as conn:
        result = conn.execute(sql)
        symbols = [row[0] for row in result]

    if not symbols:
        print("  No symbols need yfinance sector enrichment")
        return {"enriched": 0, "failed": 0, "skipped": 0}

    if yfinance_limit > 0:
        symbols = symbols[:yfinance_limit]

    print(f"  yfinance: Enriching {len(symbols)} symbols (rate={rate_limit}/sec)...")

    limiter = RateLimiter(requests_per_second=rate_limit)
    stats = {"enriched": 0, "failed": 0, "skipped": 0}

    try:
        from tqdm import tqdm
        iterator = tqdm(symbols, desc="  yfinance", unit="sym")
    except ImportError:
        iterator = symbols

    update_sql = text("""
        UPDATE us_symbol_master
        SET sector = :sector,
            industry = COALESCE(:industry, industry),
            sector_source = CASE
                WHEN sector_source IS NULL THEN 'yfinance'
                ELSE CONCAT(sector_source, '+yfinance')
            END,
            sector_updated_at = NOW(),
            updated_at = NOW()
        WHERE symbol = :symbol
    """)

    with engine.begin() as conn:
        for sym in iterator:
            limiter.acquire()
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                sector = info.get('sector')
                industry = info.get('industry')

                if sector:
                    conn.execute(update_sql, {
                        'symbol': sym,
                        'sector': sector,
                        'industry': industry,
                    })
                    stats['enriched'] += 1
                else:
                    stats['skipped'] += 1
            except Exception:
                stats['failed'] += 1

    print(f"  yfinance results: enriched={stats['enriched']}, "
          f"failed={stats['failed']}, skipped={stats['skipped']}")
    return stats


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="US 종목 마스터 동기화")
    p.add_argument("--market", choices=["NYSE", "NASDAQ", "ETF", "ALL"],
                   default="ALL", help="동기화할 마켓 (default: ALL)")
    p.add_argument("--skip-yfinance", action="store_true",
                   help="yfinance sector 보완 스킵")
    p.add_argument("--yfinance-limit", type=int, default=0,
                   help="yfinance 최대 호출 수 (0=무제한)")
    p.add_argument("--yfinance-rate", type=float, default=2.0,
                   help="yfinance 초당 요청 수 (default: 2.0)")
    return p.parse_args(argv)


def main(argv=None):
    """메인 실행 함수"""
    args = parse_args(argv)
    start_time = datetime.now()

    try:
        # 1. 설정 로드 및 DB 연결
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # 2. FDR에서 종목 목록 가져오기
        all_dfs = []

        markets_to_fetch = []
        if args.market == "ALL":
            markets_to_fetch = ["NYSE", "NASDAQ", "ETF/US"]
        elif args.market == "ETF":
            markets_to_fetch = ["ETF/US"]
        else:
            markets_to_fetch = [args.market]

        for market in markets_to_fetch:
            df = fetch_us_listing(market)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            print("Error: No symbols fetched from FDR", file=sys.stderr)
            sys.exit(1)

        fdr_df = pd.concat(all_dfs, ignore_index=True)

        # 중복 제거 (같은 심볼이 여러 마켓에 있을 수 있음)
        fdr_df = fdr_df.drop_duplicates(subset=['symbol'], keep='first')

        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Total fetched: {len(fdr_df)} symbols")

        # 3. 기존 DB 종목 로드
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loading existing symbols from DB...")
        existing_symbols = load_existing_symbols(engine)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Found {len(existing_symbols)} existing symbols in DB")

        # 4. 비교 및 분류
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Comparing symbols...")
        new_df, update_df, delisted_set = compare_and_classify(fdr_df, existing_symbols)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Classification results:")
        print(f"  - New symbols: {len(new_df)}")
        print(f"  - Symbols to update: {len(update_df)}")
        print(f"  - Delisted symbols: {len(delisted_set)}")

        # 5. DB 업데이트
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Updating us_symbol_master table...")
        stats = upsert_us_symbol_master(engine, new_df, update_df, delisted_set)

        # 6. yfinance sector 보완
        yf_stats = {"enriched": 0, "failed": 0, "skipped": 0}
        if not args.skip_yfinance:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Enriching sectors via yfinance...")
            yf_stats = enrich_sectors_yfinance(
                engine,
                rate_limit=args.yfinance_rate,
                yfinance_limit=args.yfinance_limit,
            )

        # 7. 결과 출력
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Sync completed successfully!")
        print(f"Summary:")
        print(f"  - Added: {stats['added']} symbols")
        print(f"  - Updated: {stats['updated']} symbols")
        print(f"  - Delisted: {stats['delisted']} symbols")
        if not args.skip_yfinance:
            print(f"  - yfinance enriched: {yf_stats['enriched']} symbols")
        print(f"  - Duration: {elapsed:.1f}s")

        # 8. 신규/상장폐지 종목 상세 출력 (있으면)
        if stats['added'] > 0:
            print(f"\nNew symbols added:")
            for _, row in new_df.head(10).iterrows():
                print(f"  - {row['symbol']} ({row['Name']}) [{row['Market']}]")
            if len(new_df) > 10:
                print(f"  ... and {len(new_df) - 10} more")

        if stats['delisted'] > 0:
            print(f"\nDelisted symbols:")
            for symbol in list(delisted_set)[:10]:
                print(f"  - {symbol}")
            if len(delisted_set) > 10:
                print(f"  ... and {len(delisted_set) - 10} more")

    except Exception as e:
        print(f"\n❌ Error during sync: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
