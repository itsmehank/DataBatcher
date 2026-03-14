#!/usr/bin/env python3
"""
Phase 1 테스트: sync_symbol_master.py
symbol_master 테이블에 KRX 종목 동기화가 제대로 되는지 테스트
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from sqlalchemy import text

# Import test database setup utility
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_db_setup import get_test_db_url


def cleanup_test_data(engine):
    """테스트 데이터 정리 (test database의 모든 행 삭제)"""
    print("\n[Cleanup] Removing test data from test database...")
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM symbol_master"))
        print(f"  Deleted {result.rowcount} rows from symbol_master")


def test_phase1():
    """Phase 1: Symbol Master Sync 테스트"""
    print("=" * 60)
    print("Phase 1 Test: Symbol Master Sync")
    print("=" * 60)

    # 테스트 데이터베이스 URL 설정
    print("\n[Setup] Setting up test database...")
    test_db_url = get_test_db_url()
    os.environ["DATABASE_URL"] = test_db_url
    print(f"  Using test database: trade_test")

    # 1. 설정 로드
    print("\n[1/5] Loading configuration...")
    cfg = load_settings()
    db_cfg = DBConfig(**cfg.get("database", {}))
    engine = DBManager.get_engine(db_cfg)
    print("✓ Configuration loaded with test database")

    # 2. 테이블 존재 확인
    print("\n[2/5] Checking symbol_master table...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = 'symbol_master'
        """))
        table_exists = result.scalar() > 0

    if table_exists:
        print("✓ symbol_master table exists")
    else:
        print("✗ symbol_master table does NOT exist")
        print("  Please run: python scripts/init_db.py first")
        return False

    # 3. 기존 데이터 확인
    print("\n[3/5] Checking existing data...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM symbol_master"))
        count_before = result.scalar()
        print(f"  Current symbols in DB: {count_before}")

    # 4. sync_symbol_master.py 실행
    print("\n[4/5] Running sync_symbol_master.py...")
    import subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # DATABASE_URL is already set in os.environ by test_phase1()

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_symbol_master.py")],
        capture_output=True,
        text=True,
        env=env
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"✗ Script failed with return code {result.returncode}")
        print("STDERR:", result.stderr)
        return False

    print("✓ Script completed successfully")

    # 5. 동기화 후 데이터 확인
    print("\n[5/5] Verifying synchronized data...")
    with engine.connect() as conn:
        # 전체 개수
        result = conn.execute(text("SELECT COUNT(*) FROM symbol_master"))
        count_after = result.scalar()

        # 시장별 개수
        result = conn.execute(text("""
            SELECT market, COUNT(*) as cnt
            FROM symbol_master
            WHERE status = 'ACTIVE'
            GROUP BY market
        """))
        market_counts = {row[0]: row[1] for row in result}

        # 상태별 개수
        result = conn.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM symbol_master
            GROUP BY status
        """))
        status_counts = {row[0]: row[1] for row in result}

    print(f"  Total symbols after sync: {count_after}")
    print(f"  KOSPI: {market_counts.get('KOSPI', 0)}")
    print(f"  KOSDAQ: {market_counts.get('KOSDAQ', 0)}")
    print(f"  KONEX: {market_counts.get('KONEX', 0)}")
    print(f"  ACTIVE: {status_counts.get('ACTIVE', 0)}")
    print(f"  DELISTED: {status_counts.get('DELISTED', 0)}")

    # 검증
    if count_after > 0 and status_counts.get('ACTIVE', 0) > 0:
        print("\n✅ Phase 1 TEST PASSED")
        return True
    else:
        print("\n✗ Phase 1 TEST FAILED: No active symbols found")
        return False


if __name__ == "__main__":
    try:
        success = test_phase1()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)