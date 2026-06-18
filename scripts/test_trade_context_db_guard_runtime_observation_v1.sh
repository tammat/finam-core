#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT DB GUARD RUNTIME OBSERVATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_trade_context_db_guard_runtime_observation_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_trade_context_db_guard_runtime_observation_v1.py \
  | tee /tmp/trade_context_db_guard_runtime_observation_v1.log

grep -q "TRADE_CONTEXT_DB_GUARD_RUNTIME_OBSERVATION_V1_OK" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "TRADE_CONTEXT_DB_GUARD_RUNTIME_OBSERVATION_SUMMARY" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "trigger_found=1" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "trigger_enabled=1" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "today_unknown_rows=0" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "db_update=0" /tmp/trade_context_db_guard_runtime_observation_v1.log
grep -q "VERDICT=" /tmp/trade_context_db_guard_runtime_observation_v1.log

if grep -q "VERDICT=TRADE_CONTEXT_DB_GUARD_OBSERVATION_FAILED_NEW_UNKNOWN_ROWS" /tmp/trade_context_db_guard_runtime_observation_v1.log; then
  echo "FAIL: new UNKNOWN rows detected during observation"
  exit 1
fi

curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/trade_context_db_guard_runtime_observation_today_pnl.json \
  | grep -E '"trades_today"|"context_clean"|"verdict"'

grep -q '"context_clean":1' /tmp/trade_context_db_guard_runtime_observation_today_pnl.json || \
grep -q '"context_clean": 1' /tmp/trade_context_db_guard_runtime_observation_today_pnl.json

grep -q '"verdict":"TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_runtime_observation_today_pnl.json || \
grep -q '"verdict": "TODAY_CLOSED_PNL_STATUS_OK"' /tmp/trade_context_db_guard_runtime_observation_today_pnl.json

echo
echo "=== TRADE CONTEXT DB GUARD OBSERVATION SUMMARY ==="
grep -E "trades_lookback=|known_route_trades_lookback=|unknown_lookback=|today_unknown_rows=|VERDICT=" \
  /tmp/trade_context_db_guard_runtime_observation_v1.log

echo TEST_TRADE_CONTEXT_DB_GUARD_RUNTIME_OBSERVATION_V1_OK
