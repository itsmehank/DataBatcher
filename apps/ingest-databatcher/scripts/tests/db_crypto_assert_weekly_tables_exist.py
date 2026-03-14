#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assert crypto weekly tables/views exist.

원칙
- Copilot은 DB 쿼리를 직접 실행하지 않습니다.
- 사용자가 이 스크립트를 실행하고, 출력 결과를 첨부하면 그 결과를 기반으로 다음 작업을 진행합니다.

기능
- DATABASE() 기준으로 아래 객체 존재 여부를 확인:
  - crypto_prices_weekly
  - crypto_indicators_weekly
  - v_crypto_price_weekly_with_ma

사용 예
  python scripts/tests/db_crypto_assert_weekly_tables_exist.py
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings  # noqa: E402
from core.db_manager import DBConfig, DBManager  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _exists(conn, name: str) -> bool:
    sql = """
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = :name
    LIMIT 1
    """
    r = conn.execute(text(sql), {"name": name}).fetchone()
    if r:
        return True

    # views도 tables에 들어가지만, 혹시를 대비해 views도 확인
    sql2 = """
    SELECT 1
    FROM information_schema.views
    WHERE table_schema = DATABASE()
      AND table_name = :name
    LIMIT 1
    """
    r2 = conn.execute(text(sql2), {"name": name}).fetchone()
    return bool(r2)


def main() -> int:
    cfg = load_settings()
    engine = DBManager.get_engine(DBConfig(**cfg["database"]))

    targets = [
        "crypto_prices_weekly",
        "crypto_indicators_weekly",
        "v_crypto_price_weekly_with_ma",
    ]

    print("[db] DATABASE() objects existence")
    with engine.connect() as conn:
        for t in targets:
            ok = _exists(conn, t)
            print(f"  {t}: {'OK' if ok else 'MISSING'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
