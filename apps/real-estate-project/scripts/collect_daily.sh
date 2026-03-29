#!/bin/bash
# =============================================================================
# collect_daily.sh — 일일 정기 데이터 수집
#
# 용도: cron으로 매일 실행. 전월+당월 데이터를 수집하고 분석 테이블을 갱신.
#       CLI 내부에서 최근 2개월은 기존 데이터를 삭제 후 재삽입하므로
#       중복 걱정 없이 매일 안전하게 실행 가능.
# 실행: bash scripts/collect_daily.sh
# cron: 0 21 * * *  (UTC) = 매일 오전 6시 KST
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATE_TAG=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/collect_daily_${DATE_TAG}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$PROJECT_DIR"

# .env 로드
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    log "ERROR: .env 파일이 없습니다."
    exit 1
fi

# 날짜 계산 (Linux 환경 기준)
CURRENT_YM=$(date +%Y%m)
PREV_YM=$(date -d "1 month ago" +%Y%m 2>/dev/null || date -v-1m +%Y%m)

log "=========================================="
log "일일 데이터 수집 시작"
log "수집 범위: ${PREV_YM} ~ ${CURRENT_YM}"
log "=========================================="

# 1단계: 설정 검증
log "[1/5] 환경 설정 검증 중..."
if ! python -m src.real_estate.cli validate-config --require-api-key 2>&1 | tee -a "$LOG_FILE"; then
    log "ERROR: 환경 설정 검증 실패. 수집을 중단합니다."
    exit 1
fi

# 2단계: 데이터 수집 (전월 + 당월)
log "[2/5] 데이터 수집 중 (${PREV_YM} ~ ${CURRENT_YM})..."
if ! python -m src.real_estate.cli ingest \
    --start-ymd "$PREV_YM" \
    --end-ymd "$CURRENT_YM" \
    2>&1 | tee -a "$LOG_FILE"; then
    log "WARNING: 데이터 수집 중 오류 발생. 후처리는 계속 진행합니다."
fi

# 3단계: 이상치 보정
log "[3/5] 이상치 보정 중..."
if ! python -m src.real_estate.cli clean-anomalies 2>&1 | tee -a "$LOG_FILE"; then
    log "WARNING: 이상치 보정 중 오류 발생."
fi

# 4단계: 파생 컬럼 재계산
log "[4/5] 파생 컬럼 재계산 중..."
if ! python -m src.real_estate.cli recalculate-derived 2>&1 | tee -a "$LOG_FILE"; then
    log "WARNING: 파생 컬럼 재계산 중 오류 발생."
fi

# 5단계: 분석 테이블 갱신
log "[5/5] 분석 테이블 갱신 중..."
if ! python -m src.real_estate.cli analyze 2>&1 | tee -a "$LOG_FILE"; then
    log "WARNING: 분석 테이블 갱신 중 오류 발생."
fi

log "=========================================="
log "일일 데이터 수집 완료"
log "로그 파일: $LOG_FILE"
log "=========================================="

# 7일 이상 된 로그 자동 정리
find "$LOG_DIR" -name "collect_daily_*.log" -mtime +7 -delete 2>/dev/null || true
