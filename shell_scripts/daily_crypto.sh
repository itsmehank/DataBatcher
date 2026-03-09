#!/bin/bash
# ==============================================================================
# daily_crypto.sh
#
# Crypto 일일 업데이트 (가격 + 지표)
# ==============================================================================

if [ ! -f "scripts/crypto_daily_update.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash shell_scripts/daily_crypto.sh"
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
        echo "  [$step_label] FAIL (exit=${exit_code}, ${elapsed}s)"
        ((TOTAL_FAIL++))
    fi
}

print_phase_header() {
    echo ""
    echo "============================================"
    echo " $1"
    echo "============================================"
}

print_phase_header "Crypto Daily: 가격 + 지표"

run_step "CRYPTO-1" python scripts/crypto_daily_update.py --all --with-indicators

TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " Crypto Daily 업데이트 완료"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "============================================"

if [ ${TOTAL_FAIL} -gt 0 ]; then
    exit 1
fi

exit 0
