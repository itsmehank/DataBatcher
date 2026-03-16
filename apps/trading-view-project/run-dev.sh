#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "[ERROR] backend/.venv not found."
  echo "Create it first:"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "[ERROR] frontend/node_modules not found."
  echo "Install frontend dependencies first:"
  echo "  cd frontend && npm install"
  exit 1
fi

cleanup() {
  echo ""
  echo "[INFO] Shutting down services..."
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" || true
  fi
}

trap cleanup EXIT INT TERM

echo "[INFO] Starting backend on :$BACKEND_PORT"
(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "[INFO] Starting frontend on :$FRONTEND_PORT"
cd "$FRONTEND_DIR"
npm run dev -- --port "$FRONTEND_PORT"
