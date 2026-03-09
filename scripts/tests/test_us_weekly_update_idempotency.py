#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""US stock weekly update idempotency smoke test (DB-based).

시나리오
1) 테스트 구간 데이터 cleanup
2) us_weekly_update를 동일 기준으로 2번 실행
3) counts를 확인하여 2번째 실행에서 row가 증가하지 않는지(idempotent) 확인

주의
---
이 스크립트는 다른 스크립트(us_weekly_update.py, db_us_assert_weekly_counts.py,
  db_us_weekly_cleanup.py)를 subprocess로 호출합니다.

사용 예
  python scripts/tests/test_us_weekly_update_idempotency.py --symbol AAPL --start 2024-01-01 --end 2024-03-31
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
    print("\n" + "=" * 60)
    print("STEP 1: Cleanup existing test data")
    print("=" * 60)
    rc = _run(
        [
            sys.executable,
            "scripts/tests/db_us_weekly_cleanup.py",
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
        print("\n" + "=" * 60)
        print(f"STEP 2-{i}: Run us_weekly_update.py (run #{i})")
        print("=" * 60)
        rc = _run(
            [
                sys.executable,
                "scripts/us_weekly_update.py",
                "--symbols",
                sym,
            ]
        )
        if rc != 0:
            return rc
        print(f"[run {i}] done")

    # 3) assert counts
    print("\n" + "=" * 60)
    print("STEP 3: Assert counts (check idempotency)")
    print("=" * 60)
    rc = _run(
        [
            sys.executable,
            "scripts/tests/db_us_assert_weekly_counts.py",
            "--symbol",
            sym,
            "--start",
            a.start,
            "--end",
            a.end,
        ]
    )

    print("\n" + "=" * 60)
    print("IDEMPOTENCY TEST COMPLETE")
    print("If 2nd run didn't add rows, INSERT ONLY is working correctly.")
    print("=" * 60)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
