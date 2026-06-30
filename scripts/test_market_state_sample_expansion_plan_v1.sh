#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_SAMPLE_EXPANSION_PLAN_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_sample_expansion_plan_v1.py

src/scripts/research/build_market_state_sample_expansion_plan_v1.py \
| tee /tmp/market_state_sample_expansion_plan_v1.out

grep -q "MARKET_STATE_SAMPLE_EXPANSION_PLAN_V1" \
/tmp/market_state_sample_expansion_plan_v1.out

grep -q "trade_outcomes=44" \
/tmp/market_state_sample_expansion_plan_v1.out

grep -q "TARGET name=minimum_linked_trades value=300" \
/tmp/market_state_sample_expansion_plan_v1.out

grep -q "ACTION name=continue_runtime_shadow_collection" \
/tmp/market_state_sample_expansion_plan_v1.out

grep -q "CRITERION name=research_candidate_exists" \
/tmp/market_state_sample_expansion_plan_v1.out

grep -q "VERDICT=MARKET_STATE_SAMPLE_EXPANSION_PLAN_READY" \
/tmp/market_state_sample_expansion_plan_v1.out

echo "TEST_MARKET_STATE_SAMPLE_EXPANSION_PLAN_V1_OK"
