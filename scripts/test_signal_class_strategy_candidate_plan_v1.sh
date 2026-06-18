#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS STRATEGY CANDIDATE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py \
  | tee /tmp/signal_class_strategy_candidate_plan_v1.log

grep -q "SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "SIGNAL_CLASS_STRATEGY_CANDIDATE_SUMMARY" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "promote_to_research_candidate=" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "keep_historical_research_only=" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "dirty_data_review=" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "quarantine_signal_class=" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "VERDICT=" /tmp/signal_class_strategy_candidate_plan_v1.log
grep -q "db_update=0" /tmp/signal_class_strategy_candidate_plan_v1.log

echo
echo "=== SIGNAL CLASS STRATEGY CANDIDATE SUMMARY ==="
grep -E "promote_to_research_candidate=|keep_historical_research_only=|dirty_data_review=|quarantine_signal_class=|require_more_data=|VERDICT=" \
  /tmp/signal_class_strategy_candidate_plan_v1.log

echo TEST_SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK
