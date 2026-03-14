#!/usr/bin/env python3
"""
Initialize test database (trade_test) for DataBatcher.

- Reads DATABASE_URL from environment or config, then replaces the DB name with 'trade_test'.
- Creates the database if it doesn't exist.
- Applies the same schema as init_db.py (docker/mysql/init/01_schema.sql).
- Safe to run multiple times (DDL uses IF NOT EXISTS).

Usage:
    python scripts/init_test_db.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.init_db import load_database_url, read_sql_statements, apply_schema  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

SCHEMA_FILE = ROOT / "docker" / "mysql" / "init" / "01_schema.sql"
TEST_DB_NAME = "trade_test"


def swap_db_name(url: str, new_db: str) -> str:
    """Replace the database name in a MySQL URL."""
    # Pattern: ...://user:pass@host:port/DBNAME?params
    return re.sub(r"(/)[^/?]+(\?|$)", rf"\g<1>{new_db}\2", url)


def create_database_if_not_exists(url: str, db_name: str) -> None:
    """Connect without a specific database and CREATE DATABASE IF NOT EXISTS."""
    # Remove the database portion to connect to the server root
    server_url = re.sub(r"/[^/?]+(\?)", r"/\1", url)
    if "?" not in url:
        server_url = re.sub(r"/[^/]+$", "/", url)
    engine = create_engine(server_url, future=True)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    engine.dispose()


def main():
    print(f"[init_test_db] starting... (target DB: {TEST_DB_NAME})")

    if not SCHEMA_FILE.exists():
        print(f"Schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(1)

    # Load original URL and swap DB name
    original_url = load_database_url()
    test_url = swap_db_name(original_url, TEST_DB_NAME)

    safe_test_url = test_url
    if "@" in safe_test_url and "://" in safe_test_url:
        try:
            scheme, rest = safe_test_url.split("://", 1)
            auth_host = rest.split("@", 1)
            if len(auth_host) == 2 and ":" in auth_host[0]:
                user = auth_host[0].split(":", 1)[0]
                safe_test_url = f"{scheme}://{user}:****@{auth_host[1]}"
        except Exception:
            pass

    print(f"[init_test_db] original URL DB → {TEST_DB_NAME}")
    print(f"[init_test_db] test URL: {safe_test_url}")

    # Create database if not exists
    print(f"[init_test_db] ensuring database '{TEST_DB_NAME}' exists...")
    create_database_if_not_exists(test_url, TEST_DB_NAME)

    # Apply schema
    engine = create_engine(test_url, future=True)
    stmts = read_sql_statements(SCHEMA_FILE)
    print(f"[init_test_db] applying {len(stmts)} statements from {SCHEMA_FILE.name}...")
    apply_schema(engine, stmts)
    engine.dispose()

    print(f"[init_test_db] done. Database '{TEST_DB_NAME}' is ready.")


if __name__ == "__main__":
    main()
