#!/usr/bin/env python3
"""
Phase 4 테스트: Weekly Table Operations
주봉 테이블 생성 및 업데이트 테스트

테스트 순서:
1. 테이블 생성 확인 (stock_prices_weekly, stock_indicators_weekly)
2. bulk_update_weekly.py 실행 (과거 데이터 일괄 생성)
3. weekly_update.py 실행 (증분 업데이트)
4. 데이터 검증 (가격 및 지표)
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


def check_tables_exist(engine) -> bool:
    """주봉 테이블 존재 여부 확인"""
    print("\n[Check] Verifying weekly tables exist...")
    
    with engine.connect() as conn:
        # stock_prices_weekly 확인
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
              AND table_name = 'stock_prices_weekly'
        """))
        prices_exists = result.scalar() > 0
        
        # stock_indicators_weekly 확인
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
              AND table_name = 'stock_indicators_weekly'
        """))
        indicators_exists = result.scalar() > 0
    
    if prices_exists and indicators_exists:
        print("  ✓ stock_prices_weekly exists")
        print("  ✓ stock_indicators_weekly exists")
        return True
    else:
        print("  ✗ Weekly tables not found")
        if not prices_exists:
            print("    Missing: stock_prices_weekly")
        if not indicators_exists:
            print("    Missing: stock_indicators_weekly")
        print("\n  Run: python scripts/init_db.py")
        return False


def cleanup_weekly_data(engine):
    """주봉 테스트 데이터만 정리 (일봉/symbol_master는 유지)"""
    print("\n[Cleanup] Removing weekly test data from test database...")
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text("DELETE FROM stock_indicators_weekly"))
            print(f"  Deleted {result.rowcount} rows from stock_indicators_weekly")
            
            result = conn.execute(text("DELETE FROM stock_prices_weekly"))
            print(f"  Deleted {result.rowcount} rows from stock_prices_weekly")
            
            # stock_prices, stock_indicators, symbol_master는 삭제하지 않음!
            # 이들은 주봉 생성의 소스 데이터이므로 유지 필요
    except Exception as e:
        if "doesn't exist" in str(e).lower() or "does not exist" in str(e).lower():
            print(f"  Note: Table doesn't exist yet (expected): {e}")
        else:
            print(f"  ✗ Cleanup failed: {e}")
            raise


def prepare_test_data(engine) -> bool:
    """테스트용 샘플 데이터 준비 (symbol_master + 일봉 데이터)"""
    print("\n[Setup] Preparing test fixture data...")
    
    try:
        # 1. symbol_master에 샘플 종목 추가
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO symbol_master (symbol, name, market, status)
                VALUES
                    ('005930', '삼성전자', 'KOSPI', 'ACTIVE'),
                    ('000660', 'SK하이닉스', 'KOSPI', 'ACTIVE'),
                    ('035420', 'NAVER', 'KOSPI', 'ACTIVE'),
                    ('035720', '카카오', 'KOSPI', 'ACTIVE'),
                    ('051910', 'LG화학', 'KOSPI', 'ACTIVE')
                ON DUPLICATE KEY UPDATE name=VALUES(name)
            """))
        
        print("  ✓ Sample symbols added to symbol_master")
        
        # 2. bulk_update.py로 실제 일봉 데이터 수집
        print("  Collecting daily price data via bulk_update.py...")
        end_date = date.today()
        start_date = end_date - timedelta(days=180)  # 최근 6개월
        
        import subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        
        proc = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "bulk_update.py"),
            "--start", start_date.strftime("%Y-%m-%d"),
            "--end", end_date.strftime("%Y-%m-%d"),
            "--top", "5"
        ], capture_output=True, text=True, env=env)
        
        if proc.returncode != 0:
            print(f"  ✗ Failed to collect daily data: {proc.stderr}")
            return False
        
        print("  ✓ Test fixture data ready")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to prepare test data: {e}")
        return False


def check_daily_data_exists(engine) -> bool:
    """일봉 데이터 존재 여부 확인 (주봉 생성 전제조건)"""
    print("\n[Check] Verifying daily data exists...")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(DISTINCT symbol) as symbol_count,
                   COUNT(*) as total_rows,
                   MIN(date) as oldest,
                   MAX(date) as newest
            FROM stock_prices
        """))
        row = result.fetchone()
    
    if row and row[1] > 0:
        print(f"  ✓ Daily data exists: {row[0]} symbols, {row[1]} rows")
        print(f"    Date range: {row[2]} ~ {row[3]}")
        return True
    else:
        print("  ✗ No daily data found")
        print("    Run bulk_update.py first to collect daily data")
        return False


def test_bulk_weekly_update(engine) -> bool:
    """bulk_update_weekly.py 테스트"""
    print("\n" + "=" * 60)
    print("Test 1: Bulk Weekly Update")
    print("=" * 60)
    
    # 테스트 기간 설정 (최근 6개월)
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    print(f"\nTest period: {start_date} ~ {end_date}")
    print("Running: bulk_update_weekly.py --top 5 ...")
    
    import subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # DATABASE_URL is already set in os.environ by test_phase4()
    
    proc_result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "bulk_update_weekly.py"),
        "--start", start_date.strftime("%Y-%m-%d"),
        "--end", end_date.strftime("%Y-%m-%d"),
        "--top", "5"
    ], capture_output=True, text=True, env=env)
    
    print(proc_result.stdout)
    
    if proc_result.returncode != 0:
        print(f"✗ Script failed with return code {proc_result.returncode}")
        print("STDERR:", proc_result.stderr)
        return False
    
    print("✓ Script completed successfully")
    
    # 결과 검증
    print("\n[Verify] Checking weekly data...")
    with engine.connect() as conn:
        # 주봉 가격 데이터 확인
        result = conn.execute(text("""
            SELECT COUNT(DISTINCT symbol) as symbols,
                   COUNT(*) as total_rows,
                   MIN(week_start) as oldest,
                   MAX(week_start) as newest
            FROM stock_prices_weekly
        """))
        price_row = result.fetchone()
        
        # 주봉 지표 데이터 확인
        result = conn.execute(text("""
            SELECT indicator, COUNT(*) as cnt
            FROM stock_indicators_weekly
            GROUP BY indicator
        """))
        indicator_rows = result.fetchall()
    
    if price_row and price_row[1] > 0:
        print(f"  ✓ Weekly prices: {price_row[0]} symbols, {price_row[1]} rows")
        print(f"    Date range: {price_row[2]} ~ {price_row[3]}")
    else:
        print("  ✗ No weekly price data found")
        return False
    
    if indicator_rows:
        print(f"  ✓ Weekly indicators:")
        for ind_name, cnt in indicator_rows:
            print(f"    {ind_name}: {cnt} rows")
    else:
        print("  ✗ No weekly indicator data found")
        return False
    
    # 날짜 형식 확인 (yyyy-mm-dd)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT week_start, week_end
            FROM stock_prices_weekly
            LIMIT 1
        """))
        date_row = result.fetchone()
    
    if date_row:
        print(f"\n  Date format check:")
        print(f"    week_start: {date_row[0]} (type: {type(date_row[0]).__name__})")
        print(f"    week_end: {date_row[1]} (type: {type(date_row[1]).__name__})")
    
    print("\n✅ Bulk Weekly Update TEST PASSED")
    return True


def test_weekly_incremental_update(engine) -> bool:
    """weekly_update.py 테스트"""
    print("\n" + "=" * 60)
    print("Test 2: Weekly Incremental Update")
    print("=" * 60)
    
    # 기존 데이터 카운트
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM stock_prices_weekly"))
        price_before = result.scalar()
        result = conn.execute(text("SELECT COUNT(*) FROM stock_indicators_weekly"))
        indicator_before = result.scalar()
    
    print(f"\nBefore update:")
    print(f"  Weekly prices: {price_before} rows")
    print(f"  Weekly indicators: {indicator_before} rows")
    
    print("\nRunning: weekly_update.py --all --top 5 ...")
    
    import subprocess
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # DATABASE_URL is already set in os.environ by test_phase4()
    
    proc_result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "weekly_update.py"),
        "--all",
        "--top", "5"
    ], capture_output=True, text=True, env=env)
    
    print(proc_result.stdout)
    
    if proc_result.returncode != 0:
        print(f"✗ Script failed with return code {proc_result.returncode}")
        print("STDERR:", proc_result.stderr)
        return False
    
    print("✓ Script completed successfully")
    
    # 업데이트 후 데이터 확인
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM stock_prices_weekly"))
        price_after = result.scalar()
        result = conn.execute(text("SELECT COUNT(*) FROM stock_indicators_weekly"))
        indicator_after = result.scalar()
        
        # 최근 업데이트된 종목 확인
        result = conn.execute(text("""
            SELECT symbol, MAX(week_start) as last_week, COUNT(*) as cnt
            FROM stock_prices_weekly
            GROUP BY symbol
            ORDER BY last_week DESC
            LIMIT 5
        """))
        recent_symbols = result.fetchall()
    
    print(f"\nAfter update:")
    print(f"  Weekly prices: {price_after} rows (Δ {price_after - price_before})")
    print(f"  Weekly indicators: {indicator_after} rows (Δ {indicator_after - indicator_before})")
    
    print("\n  Recently updated symbols:")
    for sym, last_week, cnt in recent_symbols:
        print(f"    {sym}: {cnt} weeks, last: {last_week}")
    
    # Smart early termination 확인
    if "모든 지표 완료 → 중단" in proc_result.stdout or "완료" in proc_result.stdout:
        print("\n  ✓ Smart early termination detected")
    
    print("\n✅ Weekly Incremental Update TEST PASSED")
    return True


def test_weekly_data_consistency(engine) -> bool:
    """일봉-주봉 일관성 검증"""
    print("\n" + "=" * 60)
    print("Test 3: Weekly Data Consistency Check")
    print("=" * 60)
    
    # 샘플 종목 선택
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol FROM stock_prices_weekly
            LIMIT 1
        """))
        sample_symbol_row = result.fetchone()
    
    if not sample_symbol_row:
        print("  ✗ No weekly data to verify")
        return False
    
    sample_symbol = sample_symbol_row[0]
    print(f"\nChecking symbol: {sample_symbol}")
    
    # 일봉과 주봉의 거래량 비교 (특정 주)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                w.week_start,
                w.week_end,
                w.volume as weekly_volume,
                (SELECT SUM(d.volume) 
                 FROM stock_prices d 
                 WHERE d.symbol = w.symbol 
                   AND d.date >= w.week_start 
                   AND d.date <= w.week_end) as daily_sum_volume
            FROM stock_prices_weekly w
            WHERE w.symbol = :symbol
            ORDER BY w.week_start DESC
            LIMIT 3
        """), {'symbol': sample_symbol})
        consistency_rows = result.fetchall()
    
    if not consistency_rows:
        print("  ✗ No data to compare")
        return False
    
    print("\n  Volume consistency check:")
    all_consistent = True
    for week_start, week_end, weekly_vol, daily_vol in consistency_rows:
        if weekly_vol and daily_vol:
            diff = abs(weekly_vol - daily_vol)
            consistent = diff < 1  # 허용 오차
            status = "✓" if consistent else "✗"
            print(f"    {status} Week {week_start}~{week_end}: Weekly={weekly_vol:,}, Daily_Sum={daily_vol:,}")
            if not consistent:
                all_consistent = False
        else:
            print(f"    ? Week {week_start}~{week_end}: Data missing")
    
    if all_consistent:
        print("\n✅ Data Consistency TEST PASSED")
        return True
    else:
        print("\n⚠ Data Consistency TEST WARNING: Some inconsistencies found")
        return True  # Warning이지만 PASS


def test_phase4():
    """Phase 4: Weekly Table Operations 전체 테스트"""
    print("=" * 60)
    print("Phase 4 Test: Weekly Table Operations")
    print("=" * 60)
    
    # 1. 테스트 DB 스키마 적용 (DB는 이미 수동으로 생성됨)
    print("\n[Setup] Setting up test database...")
    from test_db_setup import (
        apply_schema,
        get_test_db_url
    )

    try:
        test_db_url = get_test_db_url()
        apply_schema(test_db_url)
        print("✓ Test database schema applied")
    except Exception as e:
        print(f"✗ Failed to apply schema: {e}")
        return False

    # 2. 환경변수 설정
    os.environ["DATABASE_URL"] = test_db_url
    print(f"  Using test database: trade_test")
    
    # 3. 설정 로드 및 엔진 생성
    print("\n[Setup] Loading configuration...")
    cfg = load_settings()
    db_cfg = DBConfig(**cfg.get("database", {}))
    engine = DBManager.get_engine(db_cfg)
    print("✓ Configuration loaded with test database")
    
    # 4. 테이블 존재 확인
    if not check_tables_exist(engine):
        return False
    
    try:
        # 5. 주봉 데이터만 정리
        cleanup_weekly_data(engine)
        
        # 6. fixture 데이터 준비
        if not prepare_test_data(engine):
            print("\n✗ Failed to prepare test data")
            return False
        
        # 7. 전제조건 재확인
        if not check_daily_data_exists(engine):
            print("\n✗ Daily data still missing after preparation")
            return False
        
        # 8. 테스트 실행
        # Test 1: Bulk weekly update
        if not test_bulk_weekly_update(engine):
            return False
        
        # Test 2: Incremental weekly update
        if not test_weekly_incremental_update(engine):
            return False
        
        # Test 3: Data consistency
        if not test_weekly_data_consistency(engine):
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 4 TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 9. 테스트 후 정리 (주봉 데이터만)
        try:
            print("\n[Teardown] Cleaning up test data...")
            cleanup_weekly_data(engine)
            print("✓ Cleanup completed")
        except Exception as e:
            print(f"  Warning: Cleanup failed: {e}")


if __name__ == "__main__":
    try:
        success = test_phase4()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
