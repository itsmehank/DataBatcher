#!/bin/bash
# =============================================================================
# collect_initial.sh — 최초 1회 bulk 데이터 수집
#
# 용도: 서비스 최초 구축 시 bootstrap이 준비된 DB를 기준으로 2020.01부터 현재까지 전체 수집
# 실행: bash scripts/collect_initial.sh
# 주의: 수집량이 많아 1~2시간 이상 소요될 수 있습니다.
#       API 일일 호출량 제한에 걸릴 경우 다음 날 재실행하면
#       이미 수집된 데이터는 건너뛰고 나머지만 수집합니다.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/collect_initial_${TIMESTAMP}.log"

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
    log "ERROR: .env 파일이 없습니다. .env.example을 참고하여 생성하세요."
    exit 1
fi

log "=========================================="
log "최초 데이터 수집 시작"
log "프로젝트 경로: $PROJECT_DIR"
log "=========================================="

# 1단계: 설정 검증
log "[1/5] 환경 설정 검증 중..."
python -m src.real_estate.cli validate-config --require-api-key 2>&1 | tee -a "$LOG_FILE"
log "[1/5] 환경 설정 검증 완료"

# 2단계: 데이터 수집 (2020.01 ~ 현재)
CURRENT_YM=$(date +%Y%m)
START_YM="202001"
log "[2/5] 데이터 수집 시작 (${START_YM} ~ ${CURRENT_YM}, 서울 10개구)"
log "       수집 대상: gu_codes.json 기준 전체 구"
log "       소요 시간: 수집 범위에 따라 1~2시간 이상 걸릴 수 있습니다."
python -m src.real_estate.cli ingest \
    --start-ymd "$START_YM" \
    --end-ymd "$CURRENT_YM" \
    2>&1 | tee -a "$LOG_FILE"
log "[2/5] 데이터 수집 완료"

# 3단계: 이상치 보정
log "[3/5] 이상치 보정 중..."
python -m src.real_estate.cli clean-anomalies 2>&1 | tee -a "$LOG_FILE"
log "[3/5] 이상치 보정 완료"

# 4단계: 파생 컬럼 재계산
log "[4/5] 파생 컬럼 재계산 중..."
python -m src.real_estate.cli recalculate-derived 2>&1 | tee -a "$LOG_FILE"
log "[4/5] 파생 컬럼 재계산 완료"

# 5단계: 분석 테이블 생성
log "[5/5] 분석 테이블 생성 중..."
python -m src.real_estate.cli analyze 2>&1 | tee -a "$LOG_FILE"
log "[5/5] 분석 테이블 생성 완료"

log "=========================================="
log "최초 데이터 수집 완료"
log "로그 파일: $LOG_FILE"
log "=========================================="
