#!/usr/bin/env python3
"""
Initialize database schema for DataBatcher.

- Loads DATABASE_URL from environment first. If not set, tries apps/ingest-databatcher/config/settings.dev.yaml then apps/ingest-databatcher/config/settings.yaml.
- Applies SQL statements from db/init/01_schema.sql.
- Safe to run multiple times (DDL uses IF NOT EXISTS).

Note:
- Crypto(Binance) 관련 테이블도 01_schema.sql에 포함되어 있으면 본 스크립트 실행만으로 함께 생성됩니다.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List

# .env 자동 로드(선택)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore

import yaml
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

APP_ROOT = Path(__file__).resolve().parents[1]


def _resolve_schema_file() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        cand = p / "db" / "init" / "01_schema.sql"
        if cand.exists():
            return cand
    raise SystemExit("01_schema.sql not found under db/init")


SCHEMA_FILE = _resolve_schema_file()


def load_database_url() -> str:
    if load_dotenv is not None:
        load_dotenv(override=False)

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # Fallback to YAML configs
    cfg_paths = [APP_ROOT / "config" / "settings.dev.yaml", APP_ROOT / "config" / "settings.yaml"]
    repo_cfg_paths = [
        Path(__file__).resolve().parents[3] / "config" / "settings.dev.yaml",
        Path(__file__).resolve().parents[3] / "config" / "settings.yaml",
    ]
    cfg_paths.extend(repo_cfg_paths)
    for p in cfg_paths:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                db = cfg.get("database", {})
                if db.get("url"):
                    return db["url"]
    raise SystemExit("DATABASE_URL not set and no database.url found in config/settings.*.yaml")


def get_engine(url: str) -> Engine:
    return create_engine(url, future=True)


def read_sql_statements(sql_path: Path) -> List[str]:
    """Very simple splitter by semicolon; strips comments starting with -- at line start."""
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
    # naive split by ;
    parts = [stmt.strip() for stmt in cleaned.split(";")]
    return [p for p in parts if p]


def apply_schema(engine: Engine, sql_stmts: List[str]) -> None:
    with engine.begin() as conn:
        for stmt in sql_stmts:
            conn.exec_driver_sql(stmt)


def main():
    print("[init_db] starting...")
    if not SCHEMA_FILE.exists():
        print(f"Schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(1)
    db_url = load_database_url()
    safe_url = db_url
    if "@" in safe_url and "://" in safe_url:
        try:
            scheme, rest = safe_url.split("://", 1)
            auth_host = rest.split("@", 1)
            if len(auth_host) == 2 and ":" in auth_host[0]:
                user = auth_host[0].split(":", 1)[0]
                safe_url = f"{scheme}://{user}:****@{auth_host[1]}"
        except Exception:
            pass
    print(f"[init_db] using DATABASE_URL: {safe_url}")
    engine = get_engine(db_url)
    stmts = read_sql_statements(SCHEMA_FILE)
    print(f"[init_db] applying {len(stmts)} statements from {SCHEMA_FILE.name}...")
    apply_schema(engine, stmts)
    print("[init_db] done.")


if __name__ == "__main__":
    main()
