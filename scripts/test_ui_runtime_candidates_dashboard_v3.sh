#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "Источник оценки" src/ui/templates/runtime_candidates.html
grep -q "eval_trades" src/ui/templates/runtime_candidates.html
grep -q "eval_winrate" src/ui/templates/runtime_candidates.html
grep -q "eval_expectancy" src/ui/templates/runtime_candidates.html
grep -q "eval_profit_factor" src/ui/templates/runtime_candidates.html

if grep -q "Shadow Trades" src/ui/templates/runtime_candidates.html
then
  echo "RUNTIME_CANDIDATES_V3_FAIL_SHADOW_TRADES_COLUMN_PRESENT"
  exit 1
fi

if grep -q "Shadow WinRate" src/ui/templates/runtime_candidates.html
then
  echo "RUNTIME_CANDIDATES_V3_FAIL_SHADOW_WINRATE_COLUMN_PRESENT"
  exit 1
fi

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/runtime-candidates | grep -q "GDU6@RTSX"
curl -s http://127.0.0.1:8088/runtime-candidates | grep -q "SHADOW"
curl -s http://127.0.0.1:8088/runtime-candidates | grep -q "887.2273"

echo TEST_UI_RUNTIME_CANDIDATES_DASHBOARD_V3_OK
