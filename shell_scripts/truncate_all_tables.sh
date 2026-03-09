#!/bin/bash
# ==============================================================================
# truncate_all_tables.sh
#
# init_db.py(01_schema.sql)에서 생성하는 모든 테이블의 데이터를 삭제합니다.
# 테이블 구조(스키마)는 유지되며, 데이터만 삭제됩니다.
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash shell_scripts/truncate_all_tables.sh
#
# 주의:
#   - 모든 테이블의 데이터가 삭제됩니다. 복구 불가!
#   - 실행 전 반드시 확인 프롬프트가 표시됩니다.
#   - 프로젝트 루트 디렉토리에서 실행해야 합니다.
# ==============================================================================

set -e

# 프로젝트 루트 확인
if [ ! -f "scripts/table_manipulate/manage_table.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash shell_scripts/truncate_all_tables.sh"
    exit 1
fi

MANAGE="python scripts/table_manipulate/manage_table.py"

# init_db.py(01_schema.sql)에서 생성하는 전체 테이블 목록 (26개)
TABLES=(
    # KR Stock (Daily)
    stock_prices
    stock_indicators
    stock_prices_weekly
    stock_indicators_weekly
    symbol_master
    kr_sector_snapshot

    # US Stock (Daily/Weekly)
    us_stock_prices
    us_stock_indicators
    us_stock_prices_weekly
    us_stock_indicators_weekly
    us_symbol_master

    # KR Index (Daily/Weekly)
    kr_index_prices
    kr_index_indicators
    kr_index_prices_weekly
    kr_index_indicators_weekly
    kr_index_master

    # US Index (Daily/Weekly)
    us_index_prices
    us_index_indicators
    us_index_prices_weekly
    us_index_indicators_weekly
    us_index_master

    # 미너비니 템플릿 목록 테이블 (Daily)
    minervini_screen_results_kr
    minervini_screen_results_us

    # Crypto (Daily/Weekly)
    crypto_prices_daily
    crypto_indicators_daily
    crypto_prices_weekly
    crypto_indicators_weekly
    crypto_symbol_master

    # System
    sync_log
)

echo "============================================"
echo " DataBatcher - 전체 테이블 TRUNCATE"
echo "============================================"
echo ""
echo "대상 테이블 (${#TABLES[@]}개):"
for t in "${TABLES[@]}"; do
    echo "  - $t"
done
echo ""
echo "WARNING: 위 테이블의 모든 데이터가 삭제됩니다!"
echo ""
read -p "정말 진행하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""
echo "TRUNCATE 시작..."
echo ""

success=0
fail=0

for t in "${TABLES[@]}"; do
    echo -n "  $t ... "
    if $MANAGE truncate --table "$t" --yes 2>/dev/null; then
        echo "OK"
        success=$((success + 1))
    else
        echo "FAIL"
        fail=$((fail + 1))
    fi
done

echo ""
echo "============================================"
echo " 완료: 성공=${success}, 실패=${fail} / 전체=${#TABLES[@]}"
echo "============================================"
