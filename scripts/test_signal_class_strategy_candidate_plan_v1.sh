#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS STRATEGY CANDIDATE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py \
  src/scripts/research/build_signal_class_edge_scorecard_v1_1.py

PYTHONPATH=src python3 src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py \
  | tee /tmp/signal_class_strategy_candidate_plan_v1.log

grep -q "SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "SIGNAL_CLASS_STRATEGY_CANDIDATE_ROWS" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_SUMMARY" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "VERDICT=SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_READY" /tmp/signal_class_strategy_candidate_plan_v1.log

echo
echo "=== STRATEGY CANDIDATE PLAN SUMMARY ==="
grep -E "SIGNAL_CLASS_STRATEGY_CANDIDATE_ROW|rows_total=|promote_to_research_candidate=|keep_research_only=|quarantine_signal_class=|require_more_data=|legacy_dirty_data=|VERDICT=" \
  /tmp/signal_class_strategy_candidate_plan_v1.log \
  | head -180

echo TEST_SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK
