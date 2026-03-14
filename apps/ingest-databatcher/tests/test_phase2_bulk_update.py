#!/usr/bin/env python3
"""
Phase 2 테스트: bulk_update.py
소수 종목(3개)으로 병렬 수집이 제대로 작동하는지 테스트
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
                # TRUNCATE는 대량 DELETE보다 잠금 경합을 줄이고 훨씬 빠릅니다.
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


def test_phase2():
    """Phase 2: Bulk Update 테스트 (소수 종목)"""
    print("=" * 60)
    print("Phase 2 Test: Bulk Update (Sample)")
    print("=" * 60)

    # 테스트 데이터베이스 URL 설정
    print("\n[Setup] Setting up test database...")
    test_db_url = get_test_db_url()
    os.environ["DATABASE_URL"] = test_db_url
    print(f"  Using test database: trade_test")

    # 1. 설정 로드
    print("\n[1/6] Loading configuration...")
    cfg = load_settings()
    db_cfg = DBConfig(**cfg.get("database", {}))
    engine = DBManager.get_engine(db_cfg)
    print("✓ Configuration loaded with test database")

    # 2. symbol_master에서 테스트용 종목 3개 선택
    print("\n[2/6] Selecting test symbols from symbol_master...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, name, market
            FROM symbol_master
            WHERE status = 'ACTIVE'
            ORDER BY symbol
            LIMIT 3
        """))
        test_symbols = result.all()

    if len(test_symbols) < 3:
        print("✗ Not enough symbols in symbol_master")
        print("  Please run Phase 1 test first")
        return False

    print(f"  Selected test symbols:")
    for sym, name, market in test_symbols:
        print(f"    - {sym} ({name}, {market})")

    # 3. stock_prices 테이블 존재 확인
    print("\n[3/6] Checking stock_prices table...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = 'stock_prices'
        """))
        table_exists = result.scalar() > 0

    if not table_exists:
        print("✗ stock_prices table does NOT exist")
        print("  Please run: python scripts/init_db.py first")
        return False

    print("✓ stock_prices table exists")

    # 4. 기존 데이터 개수 확인
    print("\n[4/6] Checking existing price data...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM stock_prices
            WHERE symbol IN :symbols
        """), {"symbols": tuple(s[0] for s in test_symbols)})
        count_before = result.scalar()
        print(f"  Existing price records: {count_before}")

    # 5. bulk_update.py 실행 (최근 1개월치만)
    print("\n[5/6] Running bulk_update.py (recent 1 month)...")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    import subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # DATABASE_URL is already set in os.environ by test_phase2()

    subprocess_result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "bulk_update.py"),
        "--start", start_date.strftime("%Y-%m-%d"),
        "--end", end_date.strftime("%Y-%m-%d"),
        "--top", "3",
        "--workers", "2"
    ], capture_output=True, text=True, env=env)

    print(subprocess_result.stdout)
    if subprocess_result.returncode != 0:
        print(f"✗ Script failed with return code {subprocess_result.returncode}")
        print("STDERR:", subprocess_result.stderr)
        return False

    print("✓ Script completed successfully")

    # 6. 수집 후 데이터 확인
    print("\n[6/6] Verifying collected data...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM stock_prices
            WHERE symbol IN :symbols
        """), {"symbols": tuple(s[0] for s in test_symbols)})
        count_after = result.scalar()

        # 종목별 데이터 개수
        result = conn.execute(text("""
            SELECT symbol, COUNT(*) as cnt, MIN(date) as min_date, MAX(date) as max_date
            FROM stock_prices
            WHERE symbol IN :symbols
            GROUP BY symbol
        """), {"symbols": tuple(s[0] for s in test_symbols)})
        symbol_data = result.all()

    print(f"  Total price records after: {count_after}")
    print(f"  New records added: {count_after - count_before}")
    print("\n  Per-symbol breakdown:")
    for sym, cnt, min_dt, max_dt in symbol_data:
        print(f"    {sym}: {cnt} records ({min_dt} to {max_dt})")

    # stock_indicators 테이블 확인
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = 'stock_indicators'
        """))
        indicator_table_exists = result.scalar() > 0

        if indicator_table_exists:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM stock_indicators
                WHERE symbol IN :symbols
            """), {"symbols": tuple(s[0] for s in test_symbols)})
            indicator_count = result.scalar()
            print(f"\n  Indicator records: {indicator_count}")

    # 검증
    # 기존에는 '신규 데이터가 반드시 추가되어야 PASS'라서 반복 실행 시 FAIL이 발생할 수 있습니다.
    # 목표는 bulk_update 스크립트가 정상 동작하고, 최소한의 데이터/지표가 적재되었는지 확인하는 것입니다.

    collected_ok = (count_after is not None) and (count_after > 0)
    indicators_ok = True
    if indicator_table_exists:
        indicators_ok = (indicator_count is not None) and (indicator_count > 0)

    if subprocess_result.returncode == 0 and collected_ok and indicators_ok:
        print("\n✅ Phase 2 TEST PASSED")
        return True

    print("\n✗ Phase 2 TEST FAILED")
    if not collected_ok:
        print("  - No price data found for test symbols")
    if indicator_table_exists and not indicators_ok:
        print("  - No indicator data found for test symbols")
    return False


if __name__ == "__main__":
    try:
        success = test_phase2()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)