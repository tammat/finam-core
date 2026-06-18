#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT DB GUARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/apply_trade_context_db_guard_v1.py

echo
echo "=== DRY RUN ==="
PYTHONPATH=src python3 src/scripts/runtime/apply_trade_context_db_guard_v1.py \
  | tee /tmp/trade_context_db_guard_v1_dry.log

grep -q "TRADE_CONTEXT_DB_GUARD_V1_OK" /tmp/trade_context_db_guard_v1_dry.log
grep -q "VERDICT=TRADE_CONTEXT_DB_GUARD_DRY_RUN_READY" /tmp/trade_context_db_guard_v1_dry.log
grep -q "db_update=0" /tmp/trade_context_db_guard_v1_dry.log

echo
echo "=== APPLY DB GUARD ==="
APPLY=1 PYTHONPATH=src python3 src/scripts/runtime/apply_trade_context_db_guard_v1.py \
  | tee /tmp/trade_context_db_guard_v1_apply.log

grep -q "TRADE_CONTEXT_DB_GUARD_V1_OK" /tmp/trade_context_db_guard_v1_apply.log
grep -q "VERDICT=TRADE_CONTEXT_DB_GUARD_APPLY_OK" /tmp/trade_context_db_guard_v1_apply.log
grep -q "trigger_found=1" /tmp/trade_context_db_guard_v1_apply.log
grep -q "db_update=1" /tmp/trade_context_db_guard_v1_apply.log

echo
echo "=== CLEAN CURRENT UNKNOWN BACKLOG ==="
APPLY=1 PYTHONPATH=src python3 src/scripts/runtime/apply_today_pnl_unknown_trade_attribution_v1.py \
  | tee /tmp/trade_context_db_guard_v1_clean.log

grep -q "unknown_rows_after=0" /tmp/trade_context_db_guard_v1_clean.log

echo
echo "=== VERIFY DASHBOARD CLEAN ==="
curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/trade_context_db_guard_v1_today_pnl.json \
  | grep -E '"trades_today"|"context_clean"|"verdict"'

grep -q '"context_clean":1' /tmp/trade_context_db_guard_v1_today_pnl.json || \
grep -q '"context_clean": 1' /tmp/trade_context_db_guard_v1_today_pnl.json

grep -q '"verdict":"TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_v1_today_pnl.json || \
grep -q '"verdict": "TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_v1_today_pnl.json

echo TEST_TRADE_CONTEXT_DB_GUARD_V1_OK
