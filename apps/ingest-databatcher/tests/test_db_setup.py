#!/usr/bin/env python3
"""
Test Database Setup Utility

Creates and initializes a separate test database (trade_test) for testing purposes.
This prevents tests from modifying production data.

Usage:
    python tests/test_db_setup.py --create   # Create test database and schema
    python tests/test_db_setup.py --drop     # Drop test database
"""
from __future__ import annotations
import os
import argparse
from pathlib import Path
from typing import List

# .env 자동 로드(선택)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore

import yaml
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "docker" / "mysql" / "init" / "01_schema.sql"


def load_base_database_url() -> str:
    """Load database URL for deriving test DB URL.

    Precedence:
      1) Environment variable DATABASE_URL (after optional .env load)
      2) config/settings.dev.yaml
      3) config/settings.yaml
    """
    if load_dotenv is not None:
        load_dotenv(override=False)

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    cfg_paths = [ROOT / "config" / "settings.dev.yaml", ROOT / "config" / "settings.yaml"]
    for p in cfg_paths:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                db = cfg.get("database", {})
                if db.get("url"):
                    return db["url"]
    raise SystemExit("No database.url found in config/settings.*.yaml and DATABASE_URL is not set")


def get_test_database_url(base_url: str) -> str:
    """Convert production database URL to test database URL (trade_test)"""
    # Replace database name in URL
    # Format: mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4
    # Target: mysql+pymysql://user:pass@host:port/trade_test?charset=utf8mb4

    import re

    # Pattern: (prefix)/(db_name)(optional_params)
    pattern = r'(.*/)([^/?]+)(\?.*)?$'
    match = re.match(pattern, base_url)

    if not match:
        raise ValueError(f"Cannot parse database URL: {base_url}")

    prefix, db_name, params = match.groups()
    test_db_name = "trade_test"
    return f"{prefix}{test_db_name}{params or ''}"


def get_admin_url(base_url: str) -> str:
    """Get admin connection URL (without database name) for creating databases"""
    # mysql+pymysql://user:pass@host:port/dbname?params
    # -> mysql+pymysql://user:pass@host:port?params

    parts = base_url.split("/")
    if len(parts) >= 4:
        # Remove database name but keep query params
        db_and_params = parts[-1]  # e.g., "market?charset=utf8mb4"
        if "?" in db_and_params:
            params = "?" + db_and_params.split("?", 1)[1]
        else:
            params = ""
        return "/".join(parts[:-1]) + params

    raise ValueError(f"Cannot parse database URL: {base_url}")


def read_sql_statements(sql_path: Path) -> List[str]:
    """Read SQL statements from schema file"""
    text_sql = sql_path.read_text(encoding="utf-8")
    lines = []
    for raw in text_sql.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("--"):
            continue
        lines.append(raw)
    cleaned = "\n".join(lines)
    parts = [stmt.strip() for stmt in cleaned.split(";")]
    return [p for p in parts if p]


def create_test_database(base_url: str) -> str:
    """Create test database if not exists"""
    admin_url = get_admin_url(base_url)
    test_url = get_test_database_url(base_url)

    print(f"[test_db_setup] Creating test database 'trade_test'...")

    # Connect without database to create it
    engine = create_engine(admin_url, future=True)

    with engine.connect() as conn:
        # Create database if not exists
        conn.execute(text("CREATE DATABASE IF NOT EXISTS trade_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()

    engine.dispose()
    print("[test_db_setup] ✓ Test database 'trade_test' created")

    return test_url


def apply_schema(test_url: str) -> None:
    """Apply schema to test database"""
    print(f"[test_db_setup] Applying schema to test database...")

    if not SCHEMA_FILE.exists():
        raise SystemExit(f"Schema file not found: {SCHEMA_FILE}")

    engine = create_engine(test_url, future=True)
    stmts = read_sql_statements(SCHEMA_FILE)

    with engine.begin() as conn:
        for stmt in stmts:
            conn.exec_driver_sql(stmt)

    engine.dispose()
    print(f"[test_db_setup] ✓ Applied {len(stmts)} SQL statements")


def drop_test_database(base_url: str) -> None:
    """Drop test database"""
    admin_url = get_admin_url(base_url)

    print("[test_db_setup] Dropping test database 'trade_test'...")

    engine = create_engine(admin_url, future=True)

    with engine.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS trade_test"))
        conn.commit()

    engine.dispose()
    print("[test_db_setup] ✓ Test database 'trade_test' dropped")


def get_test_db_url() -> str:
    """Get test database URL for use in tests"""
    base_url = load_base_database_url()
    return get_test_database_url(base_url)


def main():
    parser = argparse.ArgumentParser(description="Test Database Setup Utility")
    parser.add_argument("--create", action="store_true", help="Create test database and apply schema")
    parser.add_argument("--drop", action="store_true", help="Drop test database")

    args = parser.parse_args()

    if not args.create and not args.drop:
        parser.print_help()
        return

    base_url = load_base_database_url()

    if args.drop:
        drop_test_database(base_url)

    if args.create:
        test_url = create_test_database(base_url)
        apply_schema(test_url)
        print(f"\n[test_db_setup] Test database ready!")
        print(f"[test_db_setup] Test DB URL: {test_url}")


if __name__ == "__main__":
    main()
