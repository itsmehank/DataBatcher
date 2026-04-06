#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUTOMATION_DIR="$ROOT_DIR/automation"
LOG_DIR="$AUTOMATION_DIR/logs"
OUTPUT_DIR="${OUTPUT_DIR:-$AUTOMATION_DIR/output}"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
REGION="${REGION:-US}"
LIST_CATEGORY="${LIST_CATEGORY:-all}"
HEADLESS="${HEADLESS:-true}"
MARKET="${MARKET:-}"
DATE_VALUE="${DATE:-}"

if [[ -z "$NODE_BIN" ]]; then
  echo "[ERROR] node executable not found"
  exit 1
fi

if [[ -z "$MARKET" ]]; then
  echo "[ERROR] MARKET environment variable is required"
  exit 1
fi

if [[ ! -d "$AUTOMATION_DIR/node_modules" ]]; then
  echo "[ERROR] automation/node_modules not found"
  echo "Run: cd $AUTOMATION_DIR && npm install && npx playwright install chromium"
  exit 1
fi

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
log_file="$LOG_DIR/dashboard_download_${timestamp}.log"

{
  echo "[INFO] dashboard download started at $(date '+%Y-%m-%d %H:%M:%S')"
  echo "[INFO] frontend_url=$FRONTEND_URL region=$REGION market=$MARKET list_category=$LIST_CATEGORY date=${DATE_VALUE:-latest-price-date}"
  curl --fail --silent --show-error "$FRONTEND_URL/api/health" >/dev/null
  curl --fail --silent --show-error "$FRONTEND_URL/api/health/db?region=$REGION" >/dev/null
  cd "$AUTOMATION_DIR"
  FRONTEND_URL="$FRONTEND_URL" \
  REGION="$REGION" \
  MARKET="$MARKET" \
  LIST_CATEGORY="$LIST_CATEGORY" \
  DATE="$DATE_VALUE" \
  HEADLESS="$HEADLESS" \
  OUTPUT_DIR="$OUTPUT_DIR" \
  "$NODE_BIN" run-dashboard-download.mjs
  echo "[INFO] dashboard download completed at $(date '+%Y-%m-%d %H:%M:%S')"
} 2>&1 | tee -a "$log_file"
