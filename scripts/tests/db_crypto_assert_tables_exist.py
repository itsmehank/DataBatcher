#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DB 검증 유틸: 코인 테이블이 실제로 생성되어 있는지 확인

사용자 실행(예):
  python scripts/tests/db_crypto_assert_tables_exist.py

출력:
- MySQL information_schema.tables에서 아래 테이블 존재 여부 출력
  - crypto_symbol_master
  - crypto_prices_daily
  - crypto_indicators_daily

주의
- Copilot은 이 파일을 실행하지 않습니다. 사용자가 실행 후 출력 결과를 첨부해주세요.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBConfig, DBManager


def main() -> int:
    cfg = load_settings()
    db_cfg = DBConfig(**cfg["database"])
    engine = DBManager.get_engine(db_cfg)

    sql = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name IN ('crypto_symbol_master','crypto_prices_daily','crypto_indicators_daily')
        ORDER BY table_name
        """
    )

    with engine.connect() as conn:
        rows = [r[0] for r in conn.execute(sql).fetchall()]

    expected = ["crypto_symbol_master", "crypto_prices_daily", "crypto_indicators_daily"]
    print("[db] DATABASE() tables existence")
    for t in expected:
        print(f"  {t}: {'OK' if t in rows else 'MISSING'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
