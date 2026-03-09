#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US Index 마스터 동기화 스크립트

S&P 500(US500), Dow Jones(DJI), NASDAQ Composite(IXIC) 지수를
us_index_master 테이블에 동기화합니다.

실행:
    python scripts/us_index_sync_master.py

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

# 하드코딩된 미국 대표 지수 목록
# FDR symbol → {market, name}
US_INDICES = {
    'US500': {'market': 'SP500', 'name': 'S&P 500'},
    'DJI':   {'market': 'DJI',   'name': 'Dow Jones Industrial Average'},
    'IXIC':  {'market': 'IXIC',  'name': 'NASDAQ Composite'},
}


def upsert_index_master(engine, indices: dict) -> dict:
    """
    us_index_master 테이블에 UPSERT

    Returns:
        {"added": N, "updated": N}
    """
    stats = {"added": 0, "updated": 0}

    sql = text("""
        INSERT INTO us_index_master (symbol, market, name, status, updated_at)
        VALUES (:symbol, :market, :name, 'ACTIVE', NOW())
        ON DUPLICATE KEY UPDATE
            market = VALUES(market),
            name = VALUES(name),
            status = 'ACTIVE',
            updated_at = NOW()
    """)

    with engine.begin() as conn:
        for symbol, info in indices.items():
            result = conn.execute(sql, {
                'symbol': symbol,
                'market': info['market'],
                'name': info['name'],
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

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] US Index Master Sync")
        print(f"  Indices: {list(US_INDICES.keys())}")

        # 지수 이름은 하드코딩 (FDR에는 지수 이름 조회 API 없음)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Index details:")
        for symbol, info in US_INDICES.items():
            print(f"  {symbol}: {info['name']} ({info['market']})")

        # DB UPSERT
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Upserting to us_index_master...")
        stats = upsert_index_master(engine, US_INDICES)

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
