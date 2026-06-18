#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EDGE RUNTIME ACTION RECOMMENDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_edge_runtime_action_recommendation_v1.py

PYTHONPATH=src python3 src/scripts/research/build_edge_runtime_action_recommendation_v1.py \
  | tee /tmp/edge_runtime_action_recommendation_v1.log

grep -q "EDGE_RUNTIME_ACTION_RECOMMENDATION_V1_OK" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "EDGE_RUNTIME_ACTION_SUMMARY" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "EDGE_ACTION_ROW" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "VERDICT=EDGE_RUNTIME_ACTION_RESTRICTIVE" /tmp/edge_runtime_action_recommendation_v1.log

grep -q "strategy=USDRUB_REGIME" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "action=QUARANTINE_RUNTIME" /tmp/edge_runtime_action_recommendation_v1.log

grep -q "strategy=BR_CONSERVATIVE_BREAKOUT" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "action=RESEARCH_ONLY_COMMISSION_DRAG" /tmp/edge_runtime_action_recommendation_v1.log

grep -q "strategy=NG_CONSERVATIVE_BREAKOUT_M1" /tmp/edge_runtime_action_recommendation_v1.log
grep -q "action=REQUIRE_MTM_FOR_OPEN_TAIL" /tmp/edge_runtime_action_recommendation_v1.log

echo TEST_EDGE_RUNTIME_ACTION_RECOMMENDATION_V1_OK
