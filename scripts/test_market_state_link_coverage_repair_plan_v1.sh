#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_state_link_coverage_repair_plan_v1.py

src/scripts/research/build_market_state_link_coverage_repair_plan_v1.py \
  | tee /tmp/market_state_link_coverage_repair_plan_v1.out

grep -q "MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_V1" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "link_ok=0" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "no_snapshot=44" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "HYPOTHESIS name=timeframe_mismatch_between_trade_outcomes_and_market_state_snapshots" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "ACTION name=audit_trade_outcomes_symbol_timeframe_ts_distribution" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "next=MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1" /tmp/market_state_link_coverage_repair_plan_v1.out
grep -q "VERDICT=MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_READY" /tmp/market_state_link_coverage_repair_plan_v1.out

echo "TEST_MARKET_STATE_LINK_COVERAGE_REPAIR_PLAN_V1_OK"
