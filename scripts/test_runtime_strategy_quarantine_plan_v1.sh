#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME STRATEGY QUARANTINE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_runtime_strategy_quarantine_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_runtime_strategy_quarantine_plan_v1.py \
  | tee /tmp/runtime_strategy_quarantine_plan_v1.log

grep -q "RUNTIME_STRATEGY_QUARANTINE_PLAN_V1_OK" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "VERDICT=RUNTIME_STRATEGY_QUARANTINE_PLAN_RESTRICTIVE" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "RUNTIME_STRATEGY_QUARANTINE_PLAN_SUMMARY" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "RUNTIME_PLAN_ROW" /tmp/runtime_strategy_quarantine_plan_v1.log

grep -q "strategy=USDRUB_REGIME" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "action=QUARANTINE_RUNTIME_CANDIDATE" /tmp/runtime_strategy_quarantine_plan_v1.log

grep -q "strategy=BR_CONSERVATIVE_BREAKOUT" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "action=RESEARCH_ONLY_COMMISSION_DRAG" /tmp/runtime_strategy_quarantine_plan_v1.log

grep -q "strategy=NG_CONSERVATIVE_BREAKOUT_M1" /tmp/runtime_strategy_quarantine_plan_v1.log
grep -q "action=REQUIRE_MTM_FOR_OPEN_TAIL" /tmp/runtime_strategy_quarantine_plan_v1.log

echo TEST_RUNTIME_STRATEGY_QUARANTINE_PLAN_V1_OK
