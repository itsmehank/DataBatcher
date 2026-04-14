#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목 마스터 동기화 스크립트 (pykrx 기반)

pykrx를 사용하여 전체 KRX 종목 목록을 가져와 symbol_master 테이블에 동기화합니다.

주요 기능:
- 신규 상장 종목 추가 (status=ACTIVE)
- 기존 종목 정보 업데이트 (name, marcap 등)
- 상장폐지 종목 상태 변경 (status=DELISTED)

변경 이력:
- 2026-01-27: FDR에서 pykrx로 전환

실행:
    python scripts/sync_symbol_master.py

주기:
    주 1회 실행 권장 (신규 상장/상장폐지 종목 감지용)
"""
from __future__ import annotations
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, Tuple, Set
import time

import pandas as pd
import requests
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from core.pykrx_adapter import fetch_krx_listing as pykrx_fetch_krx_listing
from core.pykrx_adapter import fetch_sector_classifications
from core.fdr_sector_loader import fetch_fdr_krx_sectors

try:
    from pykrx import stock
except ImportError:
    stock = None  # type: ignore[assignment]
    print("Error: pykrx not installed. Run: pip install pykrx", file=sys.stderr)
    sys.exit(1)


def fetch_kind_listing() -> pd.DataFrame:
    """KIND corpList에서 KRX 주식 목록을 조회해 표준 컬럼으로 반환.

    Returns columns:
      - symbol (str)
      - Name (str)
      - Market (str): KOSPI/KOSDAQ/KONEX
    """
    url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
    market_map = {
        "유가": "KOSPI",
        "코스닥": "KOSDAQ",
        "코넥스": "KONEX",
        "KOSPI": "KOSPI",
        "KOSDAQ": "KOSDAQ",
        "KONEX": "KONEX",
    }

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching KRX listing from KIND...")
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    html = resp.content.decode("euc-kr", "ignore")
    tables = pd.read_html(StringIO(html), flavor="lxml")
    if not tables:
        raise ValueError("KIND corpList parse returned no tables")

    df = tables[0].copy()
    required = ["회사명", "시장구분", "종목코드"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"KIND corpList missing required columns: {missing}")

    out = pd.DataFrame({
        "symbol": df["종목코드"].astype(str).str.strip().str.zfill(6).str.upper(),
        "Name": df["회사명"].astype(str).str.strip(),
        "Market": df["시장구분"].astype(str).str.strip().map(market_map).fillna(df["시장구분"].astype(str).str.strip()),
    })

    out = out.dropna(subset=["symbol", "Name", "Market"])
    out = out[out["symbol"] != ""]
    out = out.drop_duplicates(subset=["symbol"], keep="first")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] KIND listing fetched: {len(out)} symbols")
    return out


def fetch_krx_listing_with_fallback() -> tuple[pd.DataFrame, str]:
    """KRX stock listing을 pykrx 우선, 실패 시 KIND fallback으로 조회.

    Returns:
      (DataFrame, source_mode)
      source_mode in {'pykrx', 'kind_fallback'}
    """
    try:
        df = fetch_krx_listing()
        return df, "pykrx"
    except Exception as e:
        print(f"Warning: pykrx listing failed, switching to KIND fallback: {e}", file=sys.stderr)
        df_kind = fetch_kind_listing()
        if df_kind is None or df_kind.empty:
            raise ValueError("KIND fallback also returned empty result")
        return df_kind, "kind_fallback"


def fetch_krx_listing() -> pd.DataFrame:
    """
    pykrx에서 전체 KRX 종목 목록 가져오기

    Returns:
        DataFrame with columns:
        - symbol: 종목코드 (str) - 기존 Code에서 변경
        - Name: 종목명 (str)
        - Market: KOSPI/KOSDAQ/KONEX (str)
        - Marcap: 시가총액 (int)

    Raises:
        Exception: pykrx API 호출 실패 시
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching KRX listing from pykrx...")

        # pykrx_adapter의 fetch_krx_listing 사용
        # 이 함수는 Code, Name, Market, Marcap 컬럼을 반환
        df = pykrx_fetch_krx_listing()

        if df is None or df.empty:
            raise ValueError("pykrx returned empty result")

        # Code → symbol rename (adapter에서는 Code로 반환)
        if 'Code' in df.columns:
            df = df.rename(columns={'Code': 'symbol'})

        # Ensure required columns exist
        required = ['symbol', 'Name', 'Market']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetched {len(df)} symbols")
        return df

    except Exception as e:
        print(f"Error fetching KRX listing: {e}", file=sys.stderr)
        raise


def fetch_etf_listing(date_str: str | None = None, retries: int = 2, backoff_sec: float = 1.0) -> pd.DataFrame:
    """ETF 티커 목록을 pykrx 우선, 실패 시 FDR ETF/KR fallback으로 조회.

    Returns columns:
      - symbol (str)
      - Name (str)
      - Market (str): always 'ETF'
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    for attempt in range(retries + 1):
        try:
            assert stock is not None
            tickers = stock.get_etf_ticker_list(date_str)
            if not tickers:
                raise ValueError("pykrx ETF ticker list is empty")
            rows = []
            for t in tickers:
                try:
                    name = stock.get_etf_ticker_name(t)
                except Exception:
                    name = ''
                rows.append({'symbol': str(t), 'Name': str(name), 'Market': 'ETF'})
            return pd.DataFrame(rows)
        except Exception as e:
            if attempt < retries:
                time.sleep(backoff_sec * (attempt + 1))
                continue
            print(f"Warning: pykrx ETF listing failed: {e}", file=sys.stderr)

    try:
        import FinanceDataReader as fdr

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching ETF listing from FDR ETF/KR fallback...")
        etf_df = fdr.StockListing('ETF/KR')
        if etf_df is None or etf_df.empty:
            raise ValueError("FDR ETF/KR returned empty listing")

        symbol_col = 'Symbol' if 'Symbol' in etf_df.columns else etf_df.columns[0]
        name_col = 'Name' if 'Name' in etf_df.columns else etf_df.columns[1]

        out = pd.DataFrame({
            'symbol': etf_df[symbol_col].astype(str).str.strip().str.upper(),
            'Name': etf_df[name_col].astype(str).str.strip(),
            'Market': 'ETF',
        })
        out = out.drop_duplicates(subset=['symbol'], keep='first')
        out = out[out['symbol'] != '']
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ETF fallback fetched: {len(out)} symbols")
        return out
    except Exception as e:
        raise ValueError(f"Failed to fetch ETF listing from both pykrx and FDR fallback: {e}") from e

    # should be unreachable (loop either returns or raises)
    return pd.DataFrame(columns=['symbol', 'Name', 'Market'])


def load_existing_symbols(engine: Engine) -> Dict[str, Dict]:
    """
    DB에서 기존 종목 목록 로드

    Args:
        engine: SQLAlchemy engine

    Returns:
        {symbol: {name, market, status}, ...}
    """
    sql = text("""
        SELECT symbol, name, market, status
        FROM symbol_master
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

    Args:
        fdr_df: FDR에서 가져온 전체 종목 DataFrame
        existing_symbols: DB에 이미 있는 종목 {symbol: {name, market, status}}

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


def upsert_symbol_master(
    engine: Engine,
    new_symbols: pd.DataFrame,
    update_symbols: pd.DataFrame,
    delisted_symbols: Set[str]
) -> Dict[str, int]:
    """
    symbol_master 테이블 업데이트

    Args:
        engine: SQLAlchemy engine
        new_symbols: 신규 종목 DataFrame
        update_symbols: 업데이트 종목 DataFrame
        delisted_symbols: 상장폐지 종목 set

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
                INSERT INTO symbol_master
                  (symbol, market, symbol_type, name, status,
                   sector, sector_detail, industry, sector_source, sector_updated_at,
                   updated_at)
                VALUES
                  (:symbol, :market, :symbol_type, :name, 'ACTIVE',
                   :sector, :sector_detail, :industry, :sector_source,
                   CASE WHEN :sector IS NOT NULL OR :sector_detail IS NOT NULL THEN NOW() ELSE NULL END,
                   NOW())
            """)

            for _, row in new_symbols.iterrows():
                conn.execute(insert_sql, {
                    'symbol': row['symbol'],
                    'market': row['Market'],
                    'symbol_type': _val(row, 'symbol_type'),
                    'name': row['Name'],
                    'sector': _val(row, 'sector'),
                    'sector_detail': _val(row, 'sector_detail'),
                    'industry': _val(row, 'industry'),
                    'sector_source': _val(row, 'sector_source'),
                })
                stats['added'] += 1

        # 2. 기존 종목 업데이트
        if not update_symbols.empty:
            update_sql = text("""
                UPDATE symbol_master
                SET name = :name,
                    market = :market,
                    symbol_type = :symbol_type,
                    status = 'ACTIVE',
                    sector = :sector,
                    sector_detail = :sector_detail,
                    industry = :industry,
                    sector_source = :sector_source,
                    sector_updated_at = CASE WHEN :sector IS NOT NULL OR :sector_detail IS NOT NULL THEN NOW() ELSE sector_updated_at END,
                    updated_at = NOW()
                WHERE symbol = :symbol
            """)

            for _, row in update_symbols.iterrows():
                conn.execute(update_sql, {
                    'symbol': row['symbol'],
                    'market': row['Market'],
                    'symbol_type': _val(row, 'symbol_type'),
                    'name': row['Name'],
                    'sector': _val(row, 'sector'),
                    'sector_detail': _val(row, 'sector_detail'),
                    'industry': _val(row, 'industry'),
                    'sector_source': _val(row, 'sector_source'),
                })
                stats['updated'] += 1

        # 3. 상장폐지 종목 상태 변경
        if delisted_symbols:
            delist_sql = text("""
                UPDATE symbol_master
                SET status = 'DELISTED',
                    updated_at = NOW()
                WHERE symbol = :symbol
            """)

            for symbol in delisted_symbols:
                conn.execute(delist_sql, {'symbol': symbol})
                stats['delisted'] += 1

    return stats


def apply_etf_delist_guard(engine: Engine, etf_df: pd.DataFrame) -> bool:
    """ETF delist를 실행해도 되는지 여부 반환.

    Guard rules (확정):
    - len(etf_df) == 0 -> False
    - len(etf_df) < 500 -> False
    - len(etf_df) < prev_active_etf_count * 0.8 -> False
    """
    etf_count = 0 if etf_df is None else len(etf_df)
    if etf_count == 0:
        return False
    if etf_count < 500:
        return False

    with engine.connect() as conn:
        prev_count = conn.execute(
            text("SELECT COUNT(*) FROM symbol_master WHERE status='ACTIVE' AND market='ETF'")
        ).scalar_one()
    try:
        prev_count_int = int(prev_count or 0)
    except Exception:
        prev_count_int = 0

    if prev_count_int > 0 and etf_count < (prev_count_int * 0.8):
        return False

    return True


def merge_stock_and_etf_listings(stock_df: pd.DataFrame, etf_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """주식 listing + ETF listing을 결합하되, symbol 충돌은 '주식 우선/ETF 스킵'으로 처리.

    Returns:
      - merged_df
      - conflicts_df: columns [symbol, kept, skipped]
    """
    if stock_df is None:
        stock_df = pd.DataFrame()
    if etf_df is None:
        etf_df = pd.DataFrame()

    stock_df = stock_df.copy()
    etf_df = etf_df.copy()

    # fetch_krx_listing은 symbol 컬럼이 있을 수도, Code->symbol rename이 되어 있을 수도 있음
    if 'symbol' not in stock_df.columns and 'Code' in stock_df.columns:
        stock_df = stock_df.rename(columns={'Code': 'symbol'})

    # conflicts: 동일 symbol이 stock과 etf에 모두 존재
    stock_symbols = set(stock_df['symbol'].astype(str).tolist()) if 'symbol' in stock_df.columns else set()
    etf_symbols = set(etf_df['symbol'].astype(str).tolist()) if 'symbol' in etf_df.columns else set()
    conflicts = sorted(stock_symbols & etf_symbols)

    conflicts_rows = []
    if conflicts:
        # ETF 쪽에서 충돌 항목 제거
        etf_df = etf_df[~etf_df['symbol'].astype(str).isin(conflicts)].copy()
        for s in conflicts:
            # kept는 stock_df의 Market 값이 있을 가능성이 높음
            kept = None
            if 'Market' in stock_df.columns:
                m = stock_df.loc[stock_df['symbol'].astype(str) == s, 'Market']
                kept = m.iloc[0] if not m.empty else None
            conflicts_rows.append({'symbol': s, 'kept': kept or 'STOCK', 'skipped': 'ETF'})

    merged = pd.concat([stock_df, etf_df], ignore_index=True)
    return merged, pd.DataFrame(conflicts_rows)


def log_etf_conflicts(conflicts_df: pd.DataFrame, log_path: Path) -> None:
    if conflicts_df is None or conflicts_df.empty:
        return
    log_path.parent.mkdir(exist_ok=True)
    now = datetime.now().isoformat(timespec='seconds')
    with log_path.open('a', encoding='utf-8') as f:
        for _, r in conflicts_df.iterrows():
            f.write(f"{now} | SYMBOL={r['symbol']} | kept={r.get('kept','STOCK')} | skipped=ETF\n")


def main():
    """메인 실행 함수"""
    start_time = datetime.now()

    try:
        # 1. 설정 로드 및 DB 연결
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # 2. 종목 목록 가져오기 (pykrx 우선, 실패 시 KIND fallback)
        stock_df, source_mode = fetch_krx_listing_with_fallback()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stock listing source_mode={source_mode}")

        # 2-1. ETF listing fetch
        etf_df = fetch_etf_listing()

        # 2-2. merge + conflict handling
        combined_df, conflicts_df = merge_stock_and_etf_listings(stock_df, etf_df)
        conflict_log = ROOT / 'logs' / 'sync_symbol_master_etf_conflicts.log'
        log_etf_conflicts(conflicts_df, conflict_log)

        # 2-3. Sector enrichment
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Enriching sector information...")

        # symbol_type 할당: Market=='ETF' → 'ETF', 나머지 → 'STOCK'
        combined_df['symbol_type'] = combined_df['Market'].apply(
            lambda m: 'ETF' if m == 'ETF' else 'STOCK'
        )

        # pykrx 대분류 섹터 가져오기
        try:
            pykrx_sector_df = fetch_sector_classifications()
            if not pykrx_sector_df.empty:
                combined_df = combined_df.merge(
                    pykrx_sector_df, left_on='symbol', right_on='Code', how='left'
                )
                combined_df = combined_df.drop(columns=['Code'], errors='ignore')
                print(f"  pykrx sectors: {pykrx_sector_df['sector'].nunique()} unique sectors, "
                      f"{len(pykrx_sector_df)} symbols")
            else:
                combined_df['sector'] = None
        except Exception as e:
            print(f"  Warning: pykrx sector fetch failed: {e}", file=sys.stderr)
            combined_df['sector'] = None

        # FDR KRX-DESC 세분류 가져오기
        try:
            fdr_sector_df = fetch_fdr_krx_sectors()
            if not fdr_sector_df.empty:
                combined_df = combined_df.merge(
                    fdr_sector_df, left_on='symbol', right_on='Code', how='left'
                )
                combined_df = combined_df.drop(columns=['Code'], errors='ignore')
                print(f"  FDR sectors: {fdr_sector_df['sector_detail'].nunique()} unique sector_detail, "
                      f"{len(fdr_sector_df)} symbols")
            else:
                combined_df['sector_detail'] = None
                combined_df['industry'] = None
        except Exception as e:
            print(f"  Warning: FDR KRX-DESC sector fetch failed: {e}", file=sys.stderr)
            combined_df['sector_detail'] = None
            combined_df['industry'] = None

        # ETF는 sector 관련 컬럼 NULL 처리
        etf_mask = combined_df['symbol_type'] == 'ETF'
        for col in ['sector', 'sector_detail', 'industry']:
            if col in combined_df.columns:
                combined_df.loc[etf_mask, col] = None

        # sector_source 결정
        def _determine_sector_source(row):
            has_pykrx = pd.notna(row.get('sector'))
            has_fdr = pd.notna(row.get('sector_detail')) or pd.notna(row.get('industry'))
            if has_pykrx and has_fdr:
                return 'pykrx+fdr'
            elif has_pykrx:
                return 'pykrx'
            elif has_fdr:
                return 'fdr'
            return None

        combined_df['sector_source'] = combined_df.apply(_determine_sector_source, axis=1)

        sector_stats = combined_df['sector_source'].value_counts(dropna=False)
        print(f"  Sector source distribution:")
        for src, cnt in sector_stats.items():
            print(f"    {src}: {cnt}")

        fdr_df = combined_df

        # 3. 기존 DB 종목 로드
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loading existing symbols from DB...")
        existing_symbols = load_existing_symbols(engine)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Found {len(existing_symbols)} existing symbols in DB")

        # 4. 비교 및 분류
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Comparing symbols...")
        new_df, update_df, delisted_set = compare_and_classify(fdr_df, existing_symbols)

        # KIND fallback 모드에서는 목록 기반 delist를 비활성화
        if source_mode == 'kind_fallback':
            print("[sync_symbol_master] kind_fallback mode: list-based DELISTED update is disabled")
            delisted_set = set()

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Classification results:")
        print(f"  - New symbols: {len(new_df)}")
        print(f"  - Symbols to update: {len(update_df)}")
        print(f"  - Delisted symbols: {len(delisted_set)}")

        # 4-1. ETF delist guard 적용 (목록기반 delist가 활성화된 경우에만)
        if delisted_set and not apply_etf_delist_guard(engine, etf_df):
            # delisted_set 중에서 market='ETF'인 심볼은 제외
            delisted_set = {s for s in delisted_set if existing_symbols.get(s, {}).get('market') != 'ETF'}

        # 5. DB 업데이트
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Updating symbol_master table...")
        stats = upsert_symbol_master(engine, new_df, update_df, delisted_set)

        # 6. 결과 출력
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sync completed successfully!")
        print(f"Summary:")
        print(f"  - Added: {stats['added']} symbols")
        print(f"  - Updated: {stats['updated']} symbols")
        print(f"  - Delisted: {stats['delisted']} symbols")
        print(f"  - Duration: {elapsed:.1f}s")

        # 7. 신규/상장폐지 종목 상세 출력 (있으면)
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
        print(f"\nError during sync: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
