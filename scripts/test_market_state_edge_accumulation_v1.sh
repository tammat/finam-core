#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_EDGE_ACCUMULATION_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_edge_accumulation_v1.py

src/scripts/research/build_market_state_edge_accumulation_v1.py \
| tee /tmp/market_state_edge_accumulation_v1.out

grep -q "MARKET_STATE_EDGE_ACCUMULATION_V1" \
/tmp/market_state_edge_accumulation_v1.out

grep -q "STATE_ACCUMULATION" \
/tmp/market_state_edge_accumulation_v1.out

grep -q "states_total=" \
/tmp/market_state_edge_accumulation_v1.out

grep -q "observations_total=" \
/tmp/market_state_edge_accumulation_v1.out

grep -q "VERDICT=MARKET_STATE_EDGE_ACCUMULATION_READY" \
/tmp/market_state_edge_accumulation_v1.out

echo "TEST_MARKET_STATE_EDGE_ACCUMULATION_V1_OK"
