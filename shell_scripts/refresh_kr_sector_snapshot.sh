#!/bin/bash
# ==============================================================================
# refresh_kr_sector_snapshot.sh
#
# minervini_screen_results_kr의 최근 N개 거래일(unique date DESC)에 대해
# kr_sector_snapshot을 REPLACE 방식으로 갱신합니다.
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash shell_scripts/refresh_kr_sector_snapshot.sh --days 30
#
# 인자:
#   --days <N>   처리할 최근 거래일 개수 (양의 정수, 필수)
# ==============================================================================

set -euo pipefail

usage() {
    echo "Usage: bash shell_scripts/refresh_kr_sector_snapshot.sh --days <N>"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 프로젝트 루트 확인
if [ ! -f "apps/ingest-databatcher/scripts/kr_minervini_update.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    usage
    exit 1
fi

DAYS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --days|-d)
            if [ $# -lt 2 ]; then
                echo "Error: --days 값이 필요합니다."
                usage
                exit 1
            fi
            DAYS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: 알 수 없는 인자입니다: $1"
            usage
            exit 1
            ;;
    esac
done

if [ -z "${DAYS}" ]; then
    echo "Error: --days 인자는 필수입니다."
    usage
    exit 1
fi

if ! [[ "${DAYS}" =~ ^[0-9]+$ ]] || [ "${DAYS}" -le 0 ]; then
    echo "Error: --days는 1 이상의 정수여야 합니다. 입력값='${DAYS}'"
    exit 1
fi

echo "============================================"
echo " KR Sector Snapshot Refresh"
echo "============================================"
echo "  days: ${DAYS}"
echo "============================================"

python - "${DAYS}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from core.config_loader import load_settings
from core.db_manager import DBManager, DBConfig


def main() -> int:
    days = int(sys.argv[1])

    cfg = load_settings()
    db_cfg_raw = cfg.get("database")
    if not db_cfg_raw:
        print("[snapshot] Error: database 설정을 찾을 수 없습니다.", file=sys.stderr)
        return 2

    engine = DBManager.get_engine(DBConfig(**db_cfg_raw))

    select_dates_sql = text(
        """
        SELECT DISTINCT `date`
        FROM minervini_screen_results_kr
        ORDER BY `date` DESC
        LIMIT :days
        """
    )

    replace_sql = text(
        """
        REPLACE INTO kr_sector_snapshot (
          date, market, sector, symbol, name,
          close, sma_50, sma_150, sma_200,
          rs_rating, is_blue_dot, is_pass
        )
        SELECT
          :target_date AS date,
          sm.market,
          sm.sector,
          sm.symbol,
          sm.name,
          v.close,
          v.sma_50,
          v.sma_150,
          v.sma_200,
          ms.rs_rating,
          ms.is_blue_dot,
          CASE WHEN ms.symbol IS NULL THEN 0 ELSE 1 END AS is_pass
        FROM symbol_master sm
        LEFT JOIN v_stock_price_with_ma v
          ON v.symbol = sm.symbol
         AND v.date = :target_date
        LEFT JOIN minervini_screen_results_kr ms
          ON ms.symbol = sm.symbol
         AND ms.date = :target_date
         AND ms.market = sm.market
        WHERE sm.status = 'ACTIVE'
        """
    )

    with engine.connect() as conn:
        target_dates = [row[0] for row in conn.execute(select_dates_sql, {"days": days}).fetchall()]

    if not target_dates:
        print("[snapshot] 대상 날짜가 없습니다. (minervini_screen_results_kr 데이터 없음)")
        DBManager.dispose_engine()
        return 0

    print(f"[snapshot] 대상 날짜 수: {len(target_dates)}")
    for d in target_dates:
        print(f"  - {d}")

    success = 0
    fail = 0

    for target_date in target_dates:
        try:
            with engine.begin() as conn:
                result = conn.execute(replace_sql, {"target_date": target_date})
            affected = result.rowcount if result.rowcount is not None else 0
            print(f"[snapshot] OK  date={target_date} affected_rows={affected}")
            success += 1
        except Exception as e:
            print(f"[snapshot] FAIL date={target_date} error={e}", file=sys.stderr)
            fail += 1

    DBManager.dispose_engine()
    print(
        f"[snapshot] 완료: success={success}, fail={fail}, total_dates={len(target_dates)}"
    )
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
