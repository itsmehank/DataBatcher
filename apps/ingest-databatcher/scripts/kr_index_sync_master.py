#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR 지수 마스터 동기화 스크립트

KOSPI(1001), KOSDAQ(2001) 대표 지수를 kr_index_master 테이블에 동기화합니다.

실행:
    python scripts/kr_index_sync_master.py

주기:
    주 1회 실행 권장 (변경 가능성은 거의 없지만 안전을 위해)
"""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig

# 하드코딩된 대표 지수 목록
KR_INDICES = {
    '1001': 'KOSPI',
    '2001': 'KOSDAQ',
}


def fetch_index_names(indices: dict) -> dict:
    """
    pykrx에서 지수 이름 조회

    Args:
        indices: {code: market} 딕셔너리

    Returns:
        {code: name} 딕셔너리
    """
    from pykrx import stock

    names = {}
    for code in indices:
        try:
            name = stock.get_index_ticker_name(code)
            names[code] = name if name else code
        except Exception as e:
            print(f"  Warning: Failed to get name for {code}: {e}")
            names[code] = code
    return names


def upsert_index_master(engine, indices: dict, names: dict) -> dict:
    """
    kr_index_master 테이블에 UPSERT

    Returns:
        {"added": N, "updated": N}
    """
    stats = {"added": 0, "updated": 0}

    sql = text("""
        INSERT INTO kr_index_master (symbol, market, name, status, updated_at)
        VALUES (:symbol, :market, :name, 'ACTIVE', NOW())
        ON DUPLICATE KEY UPDATE
            market = VALUES(market),
            name = VALUES(name),
            status = 'ACTIVE',
            updated_at = NOW()
    """)

    with engine.begin() as conn:
        for code, market in indices.items():
            name = names.get(code, code)
            result = conn.execute(sql, {
                'symbol': code,
                'market': market,
                'name': name,
            })
            # rowcount: 1 = inserted, 2 = updated (MySQL ON DUPLICATE KEY)
            if result.rowcount == 1:
                stats['added'] += 1
            elif result.rowcount == 2:
                stats['updated'] += 1

    return stats


def main():
    start_time = datetime.now()

    try:
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] KR Index Master Sync")
        print(f"  Indices: {list(KR_INDICES.keys())}")

        # 지수 이름 조회
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching index names from pykrx...")
        names = fetch_index_names(KR_INDICES)
        for code, name in names.items():
            print(f"  {code}: {name} ({KR_INDICES[code]})")

        # DB UPSERT
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Upserting to kr_index_master...")
        stats = upsert_index_master(engine, KR_INDICES, names)

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sync completed!")
        print(f"  Added: {stats['added']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Duration: {elapsed:.1f}s")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
