#!/usr/bin/env bash
# One-command smoke test: backend tests, frontend lint + production build.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r backend/requirements-dev.txt

echo "== backend + ml + monitoring tests =="
python -m pytest -q

echo "== frontend lint =="
[ -d frontend/node_modules ] || npm --prefix frontend ci
npm --prefix frontend run lint

echo "== frontend tests =="
npm --prefix frontend run test

echo "== frontend build =="
npm --prefix frontend run build

echo "ALL CHECKS PASSED"
