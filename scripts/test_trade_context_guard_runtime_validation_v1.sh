#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT GUARD RUNTIME VALIDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_trade_context_guard_runtime_validation_v1.py
python3 -m py_compile src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py
python3 -m py_compile src/finam_core/storage/trade_context_guard_v1.py
python3 -m py_compile src/finam_core/storage/postgres_logger.py
python3 -m py_compile src/finam_core/storage/postgres.py

echo
echo "=== CLEAN CURRENT UNKNOWN BACKLOG ==="
APPLY=1 PYTHONPATH=src python3 src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py \
  | tee /tmp/trade_context_guard_runtime_validation_apply.log

grep -q "TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK" /tmp/trade_context_guard_runtime_validation_apply.log
grep -q "unknown_rows_after=0" /tmp/trade_context_guard_runtime_validation_apply.log

echo
echo "=== RESTART PAPER PIPELINE TO LOAD GUARD CODE ==="
sudo systemctl restart finam-paper-pipeline.service

sleep 5

echo
echo "=== VALIDATION IMMEDIATE ==="
PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_guard_runtime_validation_v1.py \
  | tee /tmp/trade_context_guard_runtime_validation_v1_immediate.log

grep -q "TRADE_CONTEXT_GUARD_RUNTIME_VALIDATION_V1_OK" /tmp/trade_context_guard_runtime_validation_v1_immediate.log
grep -q "service_ts_ok=1" /tmp/trade_context_guard_runtime_validation_v1_immediate.log
grep -q "unknown_after_restart=0" /tmp/trade_context_guard_runtime_validation_v1_immediate.log
grep -q "today_unknown_rows=0" /tmp/trade_context_guard_runtime_validation_v1_immediate.log

echo
echo "=== WAIT FOR RUNTIME TRADES ==="
sleep "${TRADE_CONTEXT_GUARD_RUNTIME_WAIT_SECONDS:-120}"

echo
echo "=== VALIDATION AFTER WAIT ==="
PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_guard_runtime_validation_v1.py \
  | tee /tmp/trade_context_guard_runtime_validation_v1_after_wait.log

grep -q "TRADE_CONTEXT_GUARD_RUNTIME_VALIDATION_V1_OK" /tmp/trade_context_guard_runtime_validation_v1_after_wait.log
grep -q "service_ts_ok=1" /tmp/trade_context_guard_runtime_validation_v1_after_wait.log
grep -q "unknown_after_restart=0" /tmp/trade_context_guard_runtime_validation_v1_after_wait.log
grep -q "today_unknown_rows=0" /tmp/trade_context_guard_runtime_validation_v1_after_wait.log

if grep -q "VERDICT=TRADE_CONTEXT_GUARD_RUNTIME_VALIDATION_FAILED_NEW_UNKNOWN_ROWS" /tmp/trade_context_guard_runtime_validation_v1_after_wait.log; then
  echo "FAIL: new UNKNOWN rows appeared after restart"
  exit 1
fi

curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/trade_context_guard_runtime_validation_today_pnl.json \
  | grep -E '"trades_today"|"context_clean"|"verdict"'

grep -q '"context_clean":1' /tmp/trade_context_guard_runtime_validation_today_pnl.json || \
grep -q '"context_clean": 1' /tmp/trade_context_guard_runtime_validation_today_pnl.json

grep -q '"verdict":"TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_guard_runtime_validation_today_pnl.json || \
grep -q '"verdict": "TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_guard_runtime_validation_today_pnl.json

echo
echo "=== TRADE CONTEXT GUARD RUNTIME VALIDATION SUMMARY ==="
grep -E "trades_after_restart=|known_route_trades_after_restart=|unknown_after_restart=|today_unknown_rows=|journal_guard_or_error_lines=|VERDICT=" \
  /tmp/trade_context_guard_runtime_validation_v1_after_wait.log

echo TEST_TRADE_CONTEXT_GUARD_RUNTIME_VALIDATION_V1_OK
