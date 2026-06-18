#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT DB GUARD RUNTIME VALIDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_trade_context_db_guard_runtime_validation_v1.py
python3 -m py_compile src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py

echo
echo "=== CLEAN CURRENT UNKNOWN BACKLOG ==="
APPLY=1 PYTHONPATH=src python3 src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py \
  | tee /tmp/trade_context_db_guard_runtime_validation_clean.log

grep -q "TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK" /tmp/trade_context_db_guard_runtime_validation_clean.log
grep -q "unknown_rows_after=0" /tmp/trade_context_db_guard_runtime_validation_clean.log

echo
echo "=== RESTART PAPER PIPELINE ==="
sudo systemctl restart finam-paper-pipeline.service

sleep 5

echo
echo "=== VALIDATION IMMEDIATE ==="
PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_db_guard_runtime_validation_v1.py \
  | tee /tmp/trade_context_db_guard_runtime_validation_immediate.log

grep -q "TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_V1_OK" /tmp/trade_context_db_guard_runtime_validation_immediate.log
grep -q "trigger_found=1" /tmp/trade_context_db_guard_runtime_validation_immediate.log
grep -q "trigger_enabled=1" /tmp/trade_context_db_guard_runtime_validation_immediate.log
grep -q "unknown_after_restart=0" /tmp/trade_context_db_guard_runtime_validation_immediate.log
grep -q "today_unknown_rows=0" /tmp/trade_context_db_guard_runtime_validation_immediate.log

echo
echo "=== WAIT FOR RUNTIME TRADES ==="
sleep "${TRADE_CONTEXT_DB_GUARD_RUNTIME_WAIT_SECONDS:-120}"

echo
echo "=== VALIDATION AFTER WAIT ==="
PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_db_guard_runtime_validation_v1.py \
  | tee /tmp/trade_context_db_guard_runtime_validation_after_wait.log

grep -q "TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_V1_OK" /tmp/trade_context_db_guard_runtime_validation_after_wait.log
grep -q "trigger_found=1" /tmp/trade_context_db_guard_runtime_validation_after_wait.log
grep -q "trigger_enabled=1" /tmp/trade_context_db_guard_runtime_validation_after_wait.log
grep -q "unknown_after_restart=0" /tmp/trade_context_db_guard_runtime_validation_after_wait.log
grep -q "today_unknown_rows=0" /tmp/trade_context_db_guard_runtime_validation_after_wait.log

if grep -q "VERDICT=TRADE_CONTEXT_DB_GUARD_RUNTIME_FAILED_NEW_UNKNOWN_ROWS" /tmp/trade_context_db_guard_runtime_validation_after_wait.log; then
  echo "FAIL: DB guard allowed new UNKNOWN rows"
  exit 1
fi

curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/trade_context_db_guard_runtime_validation_today_pnl.json \
  | grep -E '"trades_today"|"context_clean"|"verdict"'

grep -q '"context_clean":1' /tmp/trade_context_db_guard_runtime_validation_today_pnl.json || \
grep -q '"context_clean": 1' /tmp/trade_context_db_guard_runtime_validation_today_pnl.json

grep -q '"verdict":"TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_runtime_validation_today_pnl.json || \
grep -q '"verdict": "TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_runtime_validation_today_pnl.json

echo
echo "=== TRADE CONTEXT DB GUARD RUNTIME VALIDATION SUMMARY ==="
grep -E "trigger_found=|trigger_enabled=|trades_after_restart=|known_route_trades_after_restart=|unknown_after_restart=|today_unknown_rows=|VERDICT=" \
  /tmp/trade_context_db_guard_runtime_validation_after_wait.log

echo TEST_TRADE_CONTEXT_DB_GUARD_RUNTIME_VALIDATION_V1_OK
