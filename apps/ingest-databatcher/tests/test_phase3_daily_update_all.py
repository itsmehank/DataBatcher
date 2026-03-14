#!/usr/bin/env python3
"""
Phase 3 테스트: daily_update.py --all
--all 옵션으로 symbol_master의 모든 ACTIVE 종목을 가져오는지 테스트
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import date, timedelta

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
    """테스트 데이터 정리 (test database의 모든 행 삭제)

    Lock wait timeout(1205) 등에 대비해 TRUNCATE 우선 + retry로 정리합니다.
    """
    print("\n[Cleanup] Removing test data from test database...")

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SET SESSION innodb_lock_wait_timeout=5")
                conn.exec_driver_sql("TRUNCATE TABLE stock_indicators")
                conn.exec_driver_sql("TRUNCATE TABLE stock_prices")
                conn.exec_driver_sql("TRUNCATE TABLE symbol_master")

            print("  ✓ Cleanup completed")
            return
        except Exception as e:
            print(f"  ✗ Cleanup attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                import time

                time.sleep(0.5 * attempt)
            else:
                raise


def test_phase3():
    """Phase 3: Daily Update --all 테스트"""
    print("=" * 60)
    print("Phase 3 Test: Daily Update --all")
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

    # 2. symbol_master 확인
    print("\n[2/5] Checking symbol_master...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM symbol_master
            WHERE status = 'ACTIVE'
        """))
        active_count = result.scalar()

    if active_count == 0:
        print("✗ No ACTIVE symbols in symbol_master")
        print("  Please run Phase 1 test first")
        return False

    print(f"  ACTIVE symbols in DB: {active_count}")

    # 3. 기존 데이터 확인
    print("\n[3/5] Checking existing data...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM stock_prices"))
        price_count_before = result.scalar()
        print(f"  Existing price records: {price_count_before}")

    # 4. daily_update.py --all 실행 (상위 5개만, 최근 1주일)
    print("\n[4/5] Running daily_update.py --all --top 5...")
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    import subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # DATABASE_URL is already set in os.environ by test_phase3()

    proc_result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "daily_update.py"),
        "--all",
        "--top", "5",
        "--start", start_date.strftime("%Y-%m-%d"),
        "--end", end_date.strftime("%Y-%m-%d"),
        "--force"
    ], capture_output=True, text=True, env=env)

    print(proc_result.stdout)
    if proc_result.returncode != 0:
        print(f"✗ Script failed with return code {proc_result.returncode}")
        print("STDERR:", proc_result.stderr)
        return False

    print("✓ Script completed successfully")

    # 5. 수집 후 데이터 확인
    print("\n[5/5] Verifying collected data...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM stock_prices"))
        price_count_after = result.scalar()

        # 최근 업데이트된 종목 확인
        result = conn.execute(text("""
            SELECT symbol, MAX(date) as last_date, COUNT(*) as cnt
            FROM stock_prices
            GROUP BY symbol
            ORDER BY last_date DESC
            LIMIT 5
        """))
        recent_symbols = result.all()

    print(f"  Total price records after: {price_count_after}")
    print(f"  New records added: {price_count_after - price_count_before}")
    print("\n  Recently updated symbols:")
    for sym, last_dt, cnt in recent_symbols:
        print(f"    {sym}: {cnt} total records, last update: {last_dt}")

    # 검증: --all 옵션이 제대로 작동했는지 확인
    # 출력에 "Loaded X symbols from symbol_master" 메시지가 있는지 확인
    if "Loaded" in proc_result.stdout and "symbols from symbol_master" in proc_result.stdout:
        print("\n✓ --all option worked: symbols loaded from symbol_master")
        print("\n✅ Phase 3 TEST PASSED")
        return True
    else:
        print("\n✗ Phase 3 TEST FAILED: --all option may not have worked")
        return False


if __name__ == "__main__":
    try:
        success = test_phase3()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)