#!/bin/bash
# ==============================================================================
# bulk_all.sh
#
# 모든 시장(KR주식, US주식, Crypto, KR지수, US지수)의 bulk 데이터를
# 올바른 순서로 한 번에 수집하는 셸 스크립트입니다.
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash shell_scripts/bulk_all.sh
#
# 주의:
#   - 전체 수집은 2-3시간 소요될 수 있습니다 (US yfinance sector 수집 포함).
#   - DB 초기화(init_db.py)와 Docker MySQL이 실행 중이어야 합니다.
#   - INSERT ONLY 모드이므로 기존 데이터는 보존됩니다 (안전한 재실행 가능).
#   - 프로젝트 루트 디렉토리에서 실행해야 합니다.
# ==============================================================================

# 프로젝트 루트 확인
if [ ! -f "apps/ingest-databatcher/scripts/table_manipulate/manage_table.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash shell_scripts/bulk_all.sh"
    exit 1
fi

# ---------- YESTERDAY 계산 (macOS / Linux 호환) ----------
if date -v-1d +%Y-%m-%d > /dev/null 2>&1; then
    YESTERDAY=$(date -u -v-1d +%Y-%m-%d)
else
    YESTERDAY=$(date -u -d yesterday +%Y-%m-%d)
fi

# ---------- 설정 ----------
KR_START="2024-01-01"
US_START="2024-01-01"
CRYPTO_START="2020-01-01"
WORKERS=4

# ---------- 유틸리티 함수 ----------
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
        local elapsed=$(( $(date +%s) - start ))
        echo "  [$step_label] FAIL (exit=$?, ${elapsed}s) - 다음 단계를 계속 진행합니다."
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
#print_phase_header "Phase 0: 종목 마스터 동기화 (Sync)"
#
#run_step "0-1" python apps/ingest-databatcher/scripts/sync_symbol_master.py
#run_step "0-2" python apps/ingest-databatcher/scripts/us_sync_symbol_master.py
#run_step "0-3" python apps/ingest-databatcher/scripts/crypto_sync_symbol_master.py --all
#run_step "0-4" python apps/ingest-databatcher/scripts/kr_index_sync_master.py
#run_step "0-5" python apps/ingest-databatcher/scripts/us_index_sync_master.py

# ==============================================================================
# Phase 1: 한국 지수 (KR Index) — RS 계산의 벤치마크 선행 수집
# ==============================================================================
#print_phase_header "Phase 1: 한국 지수 (KR Index)"
#
#run_step "1-1" python apps/ingest-databatcher/scripts/kr_index_bulk_update.py --start "$KR_START" --end "$YESTERDAY"
#run_step "1-2" python apps/ingest-databatcher/scripts/kr_index_bulk_update_weekly.py

# ==============================================================================
# Phase 2: 미국 지수 (US Index) — RS 계산의 벤치마크 선행 수집
# ==============================================================================
#print_phase_header "Phase 2: 미국 지수 (US Index)"
#
#run_step "2-1" python apps/ingest-databatcher/scripts/us_index_bulk_update.py --start "$US_START" --end "$YESTERDAY"
#run_step "2-2" python apps/ingest-databatcher/scripts/us_index_bulk_update_weekly.py

# ==============================================================================
# Phase 3: 한국 주식 (KR Stock)
# ==============================================================================
print_phase_header "Phase 3: 한국 주식 (KR Stock)"

run_step "3-1" python apps/ingest-databatcher/scripts/bulk_update.py --start "$KR_START" --end "$YESTERDAY" --workers "$WORKERS"
run_step "3-2" python apps/ingest-databatcher/scripts/bulk_update_weekly.py
run_step "3-3" python apps/ingest-databatcher/scripts/kr_rs_update.py --days 9999

# ==============================================================================
# Phase 4: 미국 주식 (US Stock)
# ==============================================================================
print_phase_header "Phase 4: 미국 주식 (US Stock)"

run_step "4-1" python apps/ingest-databatcher/scripts/us_bulk_update.py --start "$US_START" --end "$YESTERDAY" --workers "$WORKERS" --with-indicators
run_step "4-2" python apps/ingest-databatcher/scripts/us_bulk_update_weekly.py
run_step "4-3" python apps/ingest-databatcher/scripts/us_rs_update.py --days 9999

# ==============================================================================
# Phase 5: 크립토 (Crypto)
# ==============================================================================
#print_phase_header "Phase 5: 크립토 (Crypto)"
#
#run_step "5-1" python apps/ingest-databatcher/scripts/crypto_bulk_update_daily.py --start "$CRYPTO_START" --end "$YESTERDAY" --with-indicators
#run_step "5-2" python apps/ingest-databatcher/scripts/crypto_bulk_update_weekly.py --start "$CRYPTO_START" --end "$YESTERDAY" --with-indicators

# ==============================================================================
# 최종 결과
# ==============================================================================
TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " 전체 Bulk 수집 완료"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "  수집 기간: KR/US=${KR_START}~${YESTERDAY}, Crypto=${CRYPTO_START}~${YESTERDAY}"
echo "============================================"
