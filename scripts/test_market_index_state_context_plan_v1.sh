#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_STATE_CONTEXT_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_index_state_context_plan_v1.py

src/scripts/research/build_market_index_state_context_plan_v1.py \
  | tee /tmp/market_index_state_context_plan_v1.out

grep -q "MARKET_INDEX_STATE_CONTEXT_PLAN_V1" /tmp/market_index_state_context_plan_v1.out
grep -q "purpose=add_index_state_context_to_market_state_edge_analysis" /tmp/market_index_state_context_plan_v1.out
grep -q "CONTEXT name=market_index_state" /tmp/market_index_state_context_plan_v1.out
grep -q "INDEX code=MOEX_INDEX" /tmp/market_index_state_context_plan_v1.out
grep -q "DIMENSION name=index_correlation_to_instrument" /tmp/market_index_state_context_plan_v1.out
grep -q "LINK_RULE name=do_not_mix_index_state_into_instrument_signature_v1" /tmp/market_index_state_context_plan_v1.out
grep -q "rule=index_context_must_be_optional" /tmp/market_index_state_context_plan_v1.out
grep -q "next=MARKET_INDEX_SOURCE_DISCOVERY_V1" /tmp/market_index_state_context_plan_v1.out
grep -q "VERDICT=MARKET_INDEX_STATE_CONTEXT_PLAN_READY" /tmp/market_index_state_context_plan_v1.out

echo "TEST_MARKET_INDEX_STATE_CONTEXT_PLAN_V1_OK"
