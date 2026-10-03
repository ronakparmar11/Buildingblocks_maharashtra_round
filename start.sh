#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

API_PID=""

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

cleanup() {
  exit_code=$?
  trap - EXIT INT TERM
  printf '\nStopping Black Box services...\n'
  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

[[ -x .venv/bin/python ]] || fail "Python environment missing. Run 'make install' first."
[[ -d frontend/node_modules ]] || fail "Frontend dependencies missing. Run 'make install' first."
command -v npm >/dev/null 2>&1 || fail "npm is not installed."
command -v curl >/dev/null 2>&1 || fail "curl is not installed."
command -v lsof >/dev/null 2>&1 || fail "lsof is not installed."

port_in_use 8000 && fail "Port 8000 is already in use. Stop the existing backend first."
port_in_use 5173 && fail "Port 5173 is already in use. Stop the existing frontend first."

export BLACKBOX_DEMO_MODE=0
export BLACKBOX_MOCK_API=0

.venv/bin/python -m uvicorn blackbox.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!

for _ in {1..50}; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    fail "The backend stopped during startup."
  fi
  sleep 0.1
done

curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1 || fail "The backend did not become healthy."

printf '\nBlack Box is running in real mode:\n'
printf '  App:     http://127.0.0.1:5173\n'
printf '  API:     http://127.0.0.1:8000\n'
printf '  Email:   SMTP settings from .env\n'
printf 'Press Ctrl+C to stop all services.\n\n'

npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173