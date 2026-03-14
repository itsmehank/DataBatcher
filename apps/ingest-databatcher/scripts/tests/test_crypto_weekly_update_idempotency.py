#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crypto weekly update idempotency smoke test (DB-based).

원칙
- Copilot은 직접 실행하지 않습니다.
- 사용자가 실행 후 출력 결과를 첨부하면, 로직을 보완합니다.

시나리오
1) 테스트 구간 데이터 cleanup
2) crypto_weekly_update를 동일 end 기준으로 2번 실행
3) counts를 확인하여 2번째 실행에서 row가 증가하지 않는지(idempotent) 확인

주의
---
이 스크립트는 다른 스크립트(crypto_weekly_update.py, db_crypto_assert_weekly_counts.py,
  db_crypto_weekly_cleanup.py)를 subprocess로 호출합니다.

사용 예
  python scripts/tests/test_crypto_weekly_update_idempotency.py --symbol BTCUSDT --start 2025-01-01 --end 2025-03-31
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    return p.parse_args()


def _run(cmd: list[str]) -> int:
    print("\n$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def main() -> int:
    a = parse_args()
    sym = a.symbol

    # 1) cleanup
    rc = _run(
        [
            sys.executable,
            "scripts/tests/db_crypto_weekly_cleanup.py",
            "--symbol",
            sym,
            "--start",
            a.start,
            "--end",
            a.end,
        ]
    )
    if rc != 0:
        return rc

    # 2) weekly_update twice (insert_only)
    for i in [1, 2]:
        rc = _run(
            [
                sys.executable,
                "scripts/crypto_weekly_update.py",
                "--symbols",
                sym,
                "--end",
                a.end,
                "--with-indicators",
                "--skip-latest-week",
            ]
        )
        if rc != 0:
            return rc
        print(f"[run {i}] done")

    # 3) assert counts
    rc = _run(
        [
            sys.executable,
            "scripts/tests/db_crypto_assert_weekly_counts.py",
            "--symbol",
            sym,
            "--start",
            a.start,
            "--end",
            a.end,
        ]
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
