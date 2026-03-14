#!/bin/bash
# ==============================================================================
# daily_all.sh
#
# 통합 Daily 실행용 래퍼(호환용)
# - daily_kr.sh
# - daily_us.sh
# - daily_crypto.sh
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash apps/ingest-databatcher/ops/shell/daily_all.sh
# ==============================================================================

if [ ! -f "apps/ingest-databatcher/ops/shell/daily_kr.sh" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash apps/ingest-databatcher/ops/shell/daily_all.sh"
    exit 1
fi

TOTAL_SUCCESS=0
TOTAL_FAIL=0
SCRIPT_START=$(date +%s)

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

print_phase_header "Phase 0: KR Daily"
run_step "0-1" bash apps/ingest-databatcher/ops/shell/daily_kr.sh

print_phase_header "Phase 1: US Daily"
run_step "1-1" bash apps/ingest-databatcher/ops/shell/daily_us.sh

print_phase_header "Phase 2: Crypto Daily"
run_step "2-1" bash apps/ingest-databatcher/ops/shell/daily_crypto.sh

TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " 전체 Daily 업데이트 완료 (통합 래퍼)"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "============================================"

if [ ${TOTAL_FAIL} -gt 0 ]; then
    exit 1
fi

exit 0
