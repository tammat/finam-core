#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FULL RUNTIME STRATEGY PAUSE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_full_runtime_strategy_pause_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_full_runtime_strategy_pause_plan_v1.py \
  | tee /tmp/full_runtime_strategy_pause_plan_v1.log

grep -q "FULL_RUNTIME_STRATEGY_PAUSE_PLAN_V1_OK" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "FULL_RUNTIME_STRATEGY_PAUSE_PLAN_SUMMARY" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "today_unknown_rows=0" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "recommended_real_trading_enabled=0" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "recommended_execution_enabled=0" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "VERDICT=" /tmp/full_runtime_strategy_pause_plan_v1.log
grep -q "db_update=0" /tmp/full_runtime_strategy_pause_plan_v1.log

if grep -q "VERDICT=FULL_RUNTIME_PAUSE_CONTEXT_DIRTY" /tmp/full_runtime_strategy_pause_plan_v1.log; then
  echo "FAIL: context dirty"
  exit 1
fi

echo
echo "=== FULL RUNTIME STRATEGY PAUSE PLAN SUMMARY ==="
grep -E "FULL_RUNTIME_PAUSE_PLAN_ROW|today_trades_total=|today_unknown_rows=|pause_candidates=|keep_shadow_observation=|runtime_changes_required=|VERDICT=" \
  /tmp/full_runtime_strategy_pause_plan_v1.log

echo TEST_FULL_RUNTIME_STRATEGY_PAUSE_PLAN_V1_OK
