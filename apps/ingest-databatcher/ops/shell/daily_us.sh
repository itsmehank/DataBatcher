#!/bin/bash
# ==============================================================================
# daily_us.sh
#
# US 일일 업데이트 (US 지수/주식 + RS + Minervini)
# ==============================================================================

if [ ! -f "apps/ingest-databatcher/scripts/us_daily_update.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash apps/ingest-databatcher/ops/shell/daily_us.sh"
    exit 1
fi

TOTAL_SUCCESS=0
TOTAL_FAIL=0
SCRIPT_START=$(date +%s)
PYTHON_BIN="${PYTHON_BIN:-python}"

run_step() {
    local step_label="$1"
    shift
    echo ""
    echo "  [$step_label] $*"
    local start=$(date +%s)
    if "$@"; then
        local elapsed=$(( $(date +%s) - start ))
        echo "  [$step_label] OK (${elapsed}s)"
        ((TOTAL_SUCCESS++))
    else
        local exit_code=$?
        local elapsed=$(( $(date +%s) - start ))
        echo "  [$step_label] FAIL (exit=${exit_code}, ${elapsed}s) - 다음 단계를 계속 진행합니다."
        ((TOTAL_FAIL++))
    fi
}

print_phase_header() {
    echo ""
    echo "============================================"
    echo " $1"
    echo "============================================"
}

print_phase_header "US Daily: 지수/주식/RS/Minervini"

run_step "US-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_index_daily_update.py --all
run_step "US-2" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_daily_update.py --all --with-indicators
run_step "US-3" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_rs_update.py --days 7
run_step "US-4" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_minervini_update.py --days 7

TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " US Daily 업데이트 완료"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "============================================"

if [ ${TOTAL_FAIL} -gt 0 ]; then
    exit 1
fi

exit 0
