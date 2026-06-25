#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_EDGE_DISCOVERY_FROM_LIVE_SHADOW_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_edge_discovery_from_live_shadow_v1.py

src/scripts/research/build_market_state_edge_discovery_from_live_shadow_v1.py \
| tee /tmp/market_state_edge_discovery_from_live_shadow_v1.out

grep -q "MARKET_STATE_EDGE_DISCOVERY_FROM_LIVE_SHADOW_V1" \
/tmp/market_state_edge_discovery_from_live_shadow_v1.out

grep -q "STATE_DISCOVERY" \
/tmp/market_state_edge_discovery_from_live_shadow_v1.out

grep -q "shadow_only=1" \
/tmp/market_state_edge_discovery_from_live_shadow_v1.out

grep -q "edge_candidates=0" \
/tmp/market_state_edge_discovery_from_live_shadow_v1.out

grep -q "VERDICT=MARKET_STATE_EDGE_DISCOVERY_SHADOW_BASELINE_READY" \
/tmp/market_state_edge_discovery_from_live_shadow_v1.out

echo "TEST_MARKET_STATE_EDGE_DISCOVERY_FROM_LIVE_SHADOW_V1_OK"
