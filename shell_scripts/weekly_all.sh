#!/bin/bash
# ==============================================================================
# weekly_all.sh
#
# 모든 시장(KR주식, US주식, Crypto, KR지수, US지수)의 주간 업데이트 및
# 종목 마스터 동기화를 올바른 순서로 한 번에 수행하는 셸 스크립트입니다.
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash shell_scripts/weekly_all.sh
#
# 주의:
#   - 주 1회 실행 권장 (토요일 또는 일요일)
#   - 전체 실행 시 30-60분 소요 (종목 마스터 동기화 포함)
#   - US 종목 마스터 동기화는 yfinance sector 수집 포함 (~1시간 소요 가능)
#   - 주말 실행 시 최신 주 포함, 평일 실행 시 최신(불완전) 주 자동 제외
#   - Docker MySQL이 실행 중이어야 합니다.
#   - 프로젝트 루트 디렉토리에서 실행해야 합니다.
# ==============================================================================

# 프로젝트 루트 확인
if [ ! -f "apps/ingest-databatcher/scripts/weekly_update.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash shell_scripts/weekly_all.sh"
    exit 1
fi

# ---------- 유틸리티 함수 ----------
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

# ==============================================================================
# Phase 0: 종목 마스터 동기화
# ==============================================================================
print_phase_header "Phase 0: 종목 마스터 동기화 (Symbol Master Sync)"

run_step "0-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/sync_symbol_master.py
run_step "0-2" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_sync_symbol_master.py
run_step "0-3" "$PYTHON_BIN" apps/ingest-databatcher/scripts/crypto_sync_symbol_master.py --all
run_step "0-4" "$PYTHON_BIN" apps/ingest-databatcher/scripts/kr_index_sync_master.py
run_step "0-5" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_index_sync_master.py

# ==============================================================================
# Phase 0.5: KR DELIST probe (14일 pykrx 검증)
# ==============================================================================
print_phase_header "Phase 0.5: KR DELIST Probe (14d pykrx)"

run_step "0-6" "$PYTHON_BIN" apps/ingest-databatcher/scripts/kr_delist_probe.py --lookback-days 14 --min-success-count 50 --min-success-ratio 0.05

# ==============================================================================
# Phase 1: 지수 주봉
# ==============================================================================
print_phase_header "Phase 1: 지수 주봉 (Index Weekly)"

run_step "1-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/kr_index_weekly_update.py --all
run_step "1-2" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_index_weekly_update.py --all

# ==============================================================================
# Phase 2: 주식 주봉
# ==============================================================================
print_phase_header "Phase 2: 주식 주봉 (Stock Weekly)"

run_step "2-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/weekly_update.py --all
run_step "2-2" "$PYTHON_BIN" apps/ingest-databatcher/scripts/us_weekly_update.py --all

# ==============================================================================
# Phase 3: Crypto 주봉
# ==============================================================================
print_phase_header "Phase 3: Crypto 주봉 (Crypto Weekly)"

run_step "3-1" "$PYTHON_BIN" apps/ingest-databatcher/scripts/crypto_weekly_update.py --all --with-indicators

# ==============================================================================
# 최종 결과
# ==============================================================================
TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " 전체 Weekly 업데이트 완료"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "============================================"

if [ ${TOTAL_FAIL} -gt 0 ]; then
    exit 1
fi

exit 0
