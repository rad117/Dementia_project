#!/usr/bin/env bash
# Start the whole platform: FastAPI backend (:8000) + React frontend (:5173).
# Usage: scripts/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r backend/requirements.txt
[ -d frontend/node_modules ] || npm --prefix frontend ci

[ -f frontend/.env.local ] || cp frontend/.env.example frontend/.env.local

uvicorn backend.main:app --port 8000 &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT INT TERM
npm --prefix frontend run dev -- --host 127.0.0.1
