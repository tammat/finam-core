#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST NG TREND UP TIME EXIT RESEARCH CANDIDATE PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_ng_trend_up_time_exit_candidate_plan_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_ng_trend_up_time_exit_candidate_plan_v1.py \
  | tee /tmp/ng_trend_up_time_exit_candidate_plan_v1.log

grep -q "NG_TREND_UP_TIME_EXIT_RESEARCH_CANDIDATE_PLAN_V1_OK" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "NG_TREND_UP_TIME_EXIT_TARGET_METRICS" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "NG_TREND_UP_TIME_EXIT_PLAN_SUMMARY" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "target_closed_cycles=" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "recommended_status=KEEP_RESEARCH_ONLY" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "VERDICT=" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log
grep -q "db_update=0" /tmp/ng_trend_up_time_exit_candidate_plan_v1.log

echo
echo "=== NG TREND UP TIME EXIT PLAN SUMMARY ==="
grep -E "target_closed_cycles=|target_net_pnl=|target_profit_factor=|days_with_target=|sibling_closed_cycles=|sibling_net_pnl=|recommended_|VERDICT=" \
  /tmp/ng_trend_up_time_exit_candidate_plan_v1.log

echo TEST_NG_TREND_UP_TIME_EXIT_RESEARCH_CANDIDATE_PLAN_V1_OK
