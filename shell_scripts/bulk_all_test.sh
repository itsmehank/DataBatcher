#!/bin/bash
# ==============================================================================
# bulk_all_test.sh
#
# bulk_all.sh의 경량 테스트 버전.
# 전체 파이프라인이 정상 동작하는지 최소 데이터로 빠르게 검증합니다.
#
# 차이점 (vs bulk_all.sh):
#   - 수집 기간: 최근 3개월
#   - KR/US 주식: 상위 3개 종목만 (--top 3)
#   - Crypto: BTCUSDT, ETHUSDT 2개만
#   - 지수: S&P 500 / KOSPI만
#   - RS 지표: 최근 5일만
#
# 예상 소요시간: 3~5분
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash shell_scripts/bulk_all_test.sh
# ==============================================================================

# 프로젝트 루트 확인
if [ ! -f "scripts/table_manipulate/manage_table.py" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash shell_scripts/bulk_all_test.sh"
    exit 1
fi

# ---------- 날짜 계산 (macOS / Linux 호환) ----------
if date -v-1d +%Y-%m-%d > /dev/null 2>&1; then
    YESTERDAY=$(date -u -v-1d +%Y-%m-%d)
    START_DATE=$(date -u -v-3m +%Y-%m-%d)
else
    YESTERDAY=$(date -u -d yesterday +%Y-%m-%d)
    START_DATE=$(date -u -d "3 months ago" +%Y-%m-%d)
fi

# ---------- 설정 ----------
WORKERS=2

echo ""
echo "============================================"
echo " bulk_all_test.sh  (경량 테스트)"
echo "============================================"
echo "  수집 기간: ${START_DATE} ~ ${YESTERDAY}"
echo "  KR/US 주식: 상위 3개 종목"
echo "  Crypto: BTCUSDT, ETHUSDT"
echo "  지수: KOSPI / SP500"
echo "============================================"

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
print_phase_header "Phase 0: 종목 마스터 동기화 (Sync)"

run_step "0-1" python scripts/sync_symbol_master.py
run_step "0-2" python scripts/us_sync_symbol_master.py --skip-yfinance
run_step "0-3" python scripts/crypto_sync_symbol_master.py --symbols BTCUSDT ETHUSDT
run_step "0-4" python scripts/kr_index_sync_master.py
run_step "0-5" python scripts/us_index_sync_master.py

# ==============================================================================
# Phase 1: 한국 지수 (KR Index) — RS 벤치마크 선행 수집
# ==============================================================================
print_phase_header "Phase 1: 한국 지수 (KR Index)"

run_step "1-1" python scripts/kr_index_bulk_update.py --start "$START_DATE" --end "$YESTERDAY" --market KOSPI
run_step "1-2" python scripts/kr_index_bulk_update_weekly.py

# ==============================================================================
# Phase 2: 미국 지수 (US Index) — RS 벤치마크 선행 수집
# ==============================================================================
print_phase_header "Phase 2: 미국 지수 (US Index)"

run_step "2-1" python scripts/us_index_bulk_update.py --start "$START_DATE" --end "$YESTERDAY" --market SP500
run_step "2-2" python scripts/us_index_bulk_update_weekly.py

# ==============================================================================
# Phase 3: 한국 주식 (KR Stock) — 상위 3개 종목만
# ==============================================================================
print_phase_header "Phase 3: 한국 주식 (KR Stock)"

run_step "3-1" python scripts/bulk_update.py --start "$START_DATE" --end "$YESTERDAY" --top 3 --workers "$WORKERS"
run_step "3-2" python scripts/bulk_update_weekly.py --top 3
run_step "3-3" python scripts/kr_rs_update.py --days 5

# ==============================================================================
# Phase 4: 미국 주식 (US Stock) — 상위 3개 종목만
# ==============================================================================
print_phase_header "Phase 4: 미국 주식 (US Stock)"

run_step "4-1" python scripts/us_bulk_update.py --start "$START_DATE" --end "$YESTERDAY" --top 3 --workers "$WORKERS" --with-indicators
run_step "4-2" python scripts/us_bulk_update_weekly.py --top 3
run_step "4-3" python scripts/us_rs_update.py --days 5

# ==============================================================================
# Phase 5: 크립토 (Crypto) — BTC, ETH만
# ==============================================================================
print_phase_header "Phase 5: 크립토 (Crypto)"

run_step "5-1" python scripts/crypto_bulk_update_daily.py --symbols BTCUSDT ETHUSDT --start "$START_DATE" --end "$YESTERDAY" --with-indicators
run_step "5-2" python scripts/crypto_bulk_update_weekly.py --symbols BTCUSDT ETHUSDT --start "$START_DATE" --end "$YESTERDAY" --with-indicators

# ==============================================================================
# 최종 결과
# ==============================================================================
TOTAL_ELAPSED=$(( $(date +%s) - SCRIPT_START ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_SEC=$(( TOTAL_ELAPSED % 60 ))

echo ""
echo "============================================"
echo " 테스트 Bulk 수집 완료"
echo "============================================"
echo "  성공: ${TOTAL_SUCCESS}"
echo "  실패: ${TOTAL_FAIL}"
echo "  소요시간: ${TOTAL_MIN}분 ${TOTAL_SEC}초"
echo "  수집 기간: ${START_DATE} ~ ${YESTERDAY}"
echo "============================================"
