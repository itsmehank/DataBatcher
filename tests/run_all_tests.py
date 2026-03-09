#!/usr/bin/env python3
"""
전체 Phase 테스트 실행 스크립트
Phase 1, 2, 3를 순차적으로 실행하고 결과를 요약합니다.
"""
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

# Add parent directory to path for imports
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig


def _cleanup_sql(conn) -> None:
    """실제 cleanup SQL 실행.

    정책:
    1) TRUNCATE 우선 시도 (빠르고 undo/row-lock 부담이 적음)
    2) TRUNCATE가 락/권한 등으로 실패하면, DELETE 폴백(순차 실행)

    주의:
    - TRUNCATE는 metadata lock이 필요해 다른 세션이 테이블을 사용 중이면 대기할 수 있습니다.
      그래서 innodb_lock_wait_timeout을 낮추고, 필요한 경우 lock_wait_timeout도 함께 낮춥니다.
    """
    # 오래 멈추지 않도록 timeout을 짧게
    conn.exec_driver_sql("SET SESSION innodb_lock_wait_timeout=2")
    # metadata lock 대기도 제한(가능한 서버에서만 적용됨)
    try:
        conn.exec_driver_sql("SET SESSION lock_wait_timeout=2")
    except Exception:
        pass

    tables = ["stock_indicators", "stock_prices", "symbol_master"]

    # 1) TRUNCATE 시도
    try:
        print("  [cleanup] trying TRUNCATE...")
        for t in tables:
            conn.exec_driver_sql(f"TRUNCATE TABLE {t}")
        return
    except Exception as e:
        print(f"  [cleanup] TRUNCATE failed -> fallback to DELETE. reason: {e}")

    # 2) DELETE 폴백 (상대적으로 락 경합이 심할 수 있음)
    print("  [cleanup] trying DELETE...")
    for t in tables:
        conn.exec_driver_sql(f"DELETE FROM {t}")


def cleanup_all_test_data():
    """모든 테스트 데이터 정리"""
    print("\n" + "=" * 70)
    print("Cleanup: Removing all test data")
    print("=" * 70)

    try:
        cfg = load_settings()
        db_cfg = DBConfig(**cfg.get("database", {}))
        engine = DBManager.get_engine(db_cfg)

        # Retry: lock wait timeout 등 일시적 경합에 대비
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with engine.connect() as conn:
                    _cleanup_sql(conn)

                print("✓ Cleanup completed successfully")
                break
            except Exception as e:
                is_last = attempt == max_attempts
                print(f"✗ Cleanup attempt {attempt}/{max_attempts} failed: {e}")
                if is_last:
                    # cleanup 실패는 테스트 결과 반환에 영향을 주지 않게(종료는 정상적으로)
                    pass
                else:
                    time.sleep(0.5 * attempt)

    finally:
        # Ensure pooled connections/threads are released so the process can exit cleanly
        DBManager.dispose_engine()


def run_test(test_name: str, test_script: Path) -> bool:
    """단일 테스트 실행"""
    print("\n" + "=" * 70)
    print(f"Running: {test_name}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, str(test_script)],
        cwd=ROOT,
    )

    return result.returncode == 0


def main() -> int:
    start_time = datetime.now()

    print("=" * 70)
    print("DataBatcher - Phase Tests")
    print("=" * 70)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("Phase 1: Symbol Master Sync", TESTS_DIR / "test_phase1_sync_symbol_master.py"),
        ("Phase 2: Bulk Update (Sample)", TESTS_DIR / "test_phase2_bulk_update.py"),
        ("Phase 3: Daily Update --all", TESTS_DIR / "test_phase3_daily_update_all.py"),
    ]

    results = {}

    for test_name, test_script in tests:
        if not test_script.exists():
            print(f"\n✗ Test script not found: {test_script}")
            results[test_name] = False
            continue

        success = run_test(test_name, test_script)
        results[test_name] = success

        if not success:
            print(f"\n⚠️  {test_name} FAILED - stopping further tests")
            break

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")

    print(f"\nTotal duration: {duration:.1f} seconds")

    all_passed = all(results.values()) if results else False

    # Cleanup after all tests
    cleanup_all_test_data()

    if all_passed:
        print("\n🎉 All tests PASSED!")
        return 0

    print("\n⚠️  Some tests FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
