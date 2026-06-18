#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME ACCUMULATION RESUME V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_runtime_accumulation_resume_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_runtime_accumulation_resume_v1.py \
  | tee /tmp/runtime_accumulation_resume_v1.log

grep -q "RUNTIME_ACCUMULATION_RESUME_V1_OK" /tmp/runtime_accumulation_resume_v1.log
grep -q "RUNTIME_ACCUMULATION_RESUME_SUMMARY" /tmp/runtime_accumulation_resume_v1.log
grep -q "today_unknown_rows=0" /tmp/runtime_accumulation_resume_v1.log
grep -q "blocked_usdrub_selection_rows=" /tmp/runtime_accumulation_resume_v1.log
grep -q "usdrub_trades_after_service_start=" /tmp/runtime_accumulation_resume_v1.log
grep -q "db_update=0" /tmp/runtime_accumulation_resume_v1.log
grep -q "VERDICT=" /tmp/runtime_accumulation_resume_v1.log

if grep -q "VERDICT=RUNTIME_ACCUMULATION_CONTEXT_DIRTY" /tmp/runtime_accumulation_resume_v1.log; then
  echo "FAIL: context dirty"
  exit 1
fi

if grep -q "VERDICT=RUNTIME_ACCUMULATION_USDRUB_STILL_TRADING" /tmp/runtime_accumulation_resume_v1.log; then
  echo "FAIL: USDRUB still trading after block"
  exit 1
fi

curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/runtime_accumulation_resume_today_pnl.json \
  | grep -E '"trades_today"|"symbols"|"closed_cycles"|"context_clean"|"net_pnl"|"verdict"'

grep -q '"context_clean":1' /tmp/runtime_accumulation_resume_today_pnl.json || \
grep -q '"context_clean": 1' /tmp/runtime_accumulation_resume_today_pnl.json

echo
echo "=== RUNTIME ACCUMULATION RESUME SUMMARY ==="
grep -E "today_trades_total=|today_unknown_rows=|blocked_usdrub_selection_rows=|usdrub_trades_after_service_start=|active_enabled_symbols=|VERDICT=" \
  /tmp/runtime_accumulation_resume_v1.log

echo TEST_RUNTIME_ACCUMULATION_RESUME_V1_OK
