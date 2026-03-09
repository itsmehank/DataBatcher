#!/usr/bin/env python3
"""
MySQL 테이블 관리 통합 스크립트

Usage:
  python manage_table.py drop --table stock_prices
  python manage_table.py truncate --table stock_indicators
  python manage_table.py delete-symbol --table stock_prices --symbol 005930
  python manage_table.py delete-rows --table stock_indicators --symbol 005930 --column indicator --value sma_5_close
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 추가
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig
from sqlalchemy import text


def drop_table(engine, table_name: str, dry_run: bool = False):
    """테이블 삭제"""
    sql = f"DROP TABLE IF EXISTS {table_name}"
    
    if dry_run:
        print(f"[DRY-RUN] {sql}")
        return
    
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"✅ Table '{table_name}' dropped successfully.")


def truncate_table(engine, table_name: str, dry_run: bool = False):
    """테이블 데이터 삭제 (구조 유지)"""
    sql = f"TRUNCATE TABLE {table_name}"
    
    if dry_run:
        print(f"[DRY-RUN] {sql}")
        return
    
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"✅ Table '{table_name}' truncated successfully.")


def delete_by_symbol(engine, table_name: str, symbol: str, dry_run: bool = False):
    """특정 symbol의 모든 행 삭제"""
    # 먼저 삭제될 행 수 확인
    count_sql = f"SELECT COUNT(*) FROM {table_name} WHERE symbol = :symbol"
    with engine.connect() as conn:
        count = conn.execute(text(count_sql), {"symbol": symbol}).scalar()
    
    if count == 0:
        print(f"⚠️ No rows found for symbol '{symbol}' in '{table_name}'.")
        return
    
    delete_sql = f"DELETE FROM {table_name} WHERE symbol = :symbol"
    
    if dry_run:
        print(f"[DRY-RUN] {delete_sql} (will delete {count} rows)")
        return
    
    with engine.begin() as conn:
        conn.execute(text(delete_sql), {"symbol": symbol})
    print(f"✅ Deleted {count} rows for symbol '{symbol}' from '{table_name}'.")


def delete_by_condition(engine, table_name: str, symbol: str, column: str, value: str, dry_run: bool = False):
    """특정 symbol과 조건에 맞는 행 삭제"""
    # 먼저 삭제될 행 수 확인
    count_sql = f"SELECT COUNT(*) FROM {table_name} WHERE symbol = :symbol AND {column} = :value"
    with engine.connect() as conn:
        count = conn.execute(text(count_sql), {"symbol": symbol, "value": value}).scalar()
    
    if count == 0:
        print(f"⚠️ No rows found for symbol='{symbol}' AND {column}='{value}' in '{table_name}'.")
        return
    
    delete_sql = f"DELETE FROM {table_name} WHERE symbol = :symbol AND {column} = :value"
    
    if dry_run:
        print(f"[DRY-RUN] {delete_sql} (will delete {count} rows)")
        return
    
    with engine.begin() as conn:
        conn.execute(text(delete_sql), {"symbol": symbol, "value": value})
    print(f"✅ Deleted {count} rows for symbol='{symbol}' AND {column}='{value}' from '{table_name}'.")


def confirm_action(message: str) -> bool:
    """사용자 확인"""
    response = input(f"{message} (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def main():
    parser = argparse.ArgumentParser(
        description="DataBatcher MySQL 테이블 관리 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 테이블 삭제
  python manage_table.py drop --table stock_prices
  
  # 테이블 데이터만 삭제 (구조 유지)
  python manage_table.py truncate --table stock_indicators
  
  # 특정 종목의 모든 데이터 삭제
  python manage_table.py delete-symbol --table stock_prices --symbol 005930
  
  # 특정 종목의 특정 지표만 삭제
  python manage_table.py delete-rows --table stock_indicators --symbol 005930 --column indicator --value sma_5_close
  
  # Dry-run (실행하지 않고 SQL만 출력)
  python manage_table.py drop --table stock_prices --dry-run
  
  # 확인 프롬프트 생략
  python manage_table.py truncate --table stock_prices --yes
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # drop 서브커맨드
    drop_parser = subparsers.add_parser('drop', help='테이블 삭제')
    drop_parser.add_argument('--table', required=True, help='테이블 이름')
    drop_parser.add_argument('--yes', action='store_true', help='확인 프롬프트 생략')
    drop_parser.add_argument('--dry-run', action='store_true', help='SQL만 출력 (실행 안 함)')
    
    # truncate 서브커맨드
    truncate_parser = subparsers.add_parser('truncate', help='테이블 데이터 삭제 (구조 유지)')
    truncate_parser.add_argument('--table', required=True, help='테이블 이름')
    truncate_parser.add_argument('--yes', action='store_true', help='확인 프롬프트 생략')
    truncate_parser.add_argument('--dry-run', action='store_true', help='SQL만 출력 (실행 안 함)')
    
    # delete-symbol 서브커맨드
    delete_symbol_parser = subparsers.add_parser('delete-symbol', help='특정 symbol의 모든 행 삭제')
    delete_symbol_parser.add_argument('--table', required=True, help='테이블 이름')
    delete_symbol_parser.add_argument('--symbol', required=True, help='종목 코드 (예: 005930)')
    delete_symbol_parser.add_argument('--yes', action='store_true', help='확인 프롬프트 생략')
    delete_symbol_parser.add_argument('--dry-run', action='store_true', help='SQL만 출력 (실행 안 함)')
    
    # delete-rows 서브커맨드
    delete_rows_parser = subparsers.add_parser('delete-rows', help='조건에 맞는 행 삭제')
    delete_rows_parser.add_argument('--table', required=True, help='테이블 이름')
    delete_rows_parser.add_argument('--symbol', required=True, help='종목 코드 (예: 005930)')
    delete_rows_parser.add_argument('--column', required=True, help='컬럼 이름 (예: indicator)')
    delete_rows_parser.add_argument('--value', required=True, help='컬럼 값 (예: sma_5_close)')
    delete_rows_parser.add_argument('--yes', action='store_true', help='확인 프롬프트 생략')
    delete_rows_parser.add_argument('--dry-run', action='store_true', help='SQL만 출력 (실행 안 함)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # DB 연결
    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))
    
    # 명령 실행
    try:
        if args.command == 'drop':
            if not args.yes and not args.dry_run:
                if not confirm_action(f"⚠️ DROP table '{args.table}'?"):
                    print("Cancelled.")
                    sys.exit(0)
            drop_table(engine, args.table, args.dry_run)
        
        elif args.command == 'truncate':
            if not args.yes and not args.dry_run:
                if not confirm_action(f"⚠️ TRUNCATE table '{args.table}'?"):
                    print("Cancelled.")
                    sys.exit(0)
            truncate_table(engine, args.table, args.dry_run)
        
        elif args.command == 'delete-symbol':
            if not args.yes and not args.dry_run:
                if not confirm_action(f"⚠️ DELETE all rows for symbol '{args.symbol}' from '{args.table}'?"):
                    print("Cancelled.")
                    sys.exit(0)
            delete_by_symbol(engine, args.table, args.symbol, args.dry_run)
        
        elif args.command == 'delete-rows':
            if not args.yes and not args.dry_run:
                if not confirm_action(f"⚠️ DELETE rows where symbol='{args.symbol}' AND {args.column}='{args.value}' from '{args.table}'?"):
                    print("Cancelled.")
                    sys.exit(0)
            delete_by_condition(engine, args.table, args.symbol, args.column, args.value, args.dry_run)
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
