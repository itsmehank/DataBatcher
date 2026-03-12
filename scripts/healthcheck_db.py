from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


def main() -> int:
    cfg = load_settings()
    db_cfg = cfg.get("database")
    if not db_cfg:
        print("[healthcheck_db] database 설정이 없습니다.", file=sys.stderr)
        return 2

    try:
        engine = DBManager.get_engine(DBConfig(**db_cfg))
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[healthcheck_db] DB connection OK")
        return 0
    except Exception as e:
        print(f"[healthcheck_db] DB connection FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        DBManager.dispose_engine()


if __name__ == "__main__":
    raise SystemExit(main())
