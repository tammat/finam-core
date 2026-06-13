#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "gold_status.html" src/ui/readonly_runtime_dashboard_v1.py
grep -q "GOLD: статус жизненного цикла" src/ui/templates/gold_status.html
grep -q "Shadow Trades" src/ui/templates/gold_status.html
grep -q "WalkForward" src/ui/templates/gold_status.html
grep -q "Candidate Registry" src/ui/templates/gold_status.html
grep -q "Runtime Approval" src/ui/templates/gold_status.html

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold | grep -q "GOLD: статус жизненного цикла"
curl -s http://127.0.0.1:8088/gold | grep -q "Кандидат для runtime-наблюдения"

echo TEST_UI_GOLD_STATUS_V2_OK
