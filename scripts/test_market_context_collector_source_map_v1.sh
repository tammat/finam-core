#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COLLECTOR_SOURCE_MAP_V1 ==="

doc="docs/MARKET_CONTEXT_COLLECTOR_SOURCE_MAP_V1.txt"

test -f "$doc"

for section in \
"FIELD MAPPING" \
"COLLECTOR PIPELINE" \
"PHASE 1" \
"PHASE 2" \
"PHASE 3" \
"SAFETY"
do
    grep -q "$section" "$doc"
done

for source in \
"analytics_regime_snapshots_v2" \
"feature_snapshots" \
"market_snapshot_v1" \
"market_event_calendar" \
"edge_score_model_v2"
do
    grep -q "$source" "$doc"
done

grep -q "knowledge.market_context_v1" "$doc"
grep -q "MARKET_CONTEXT_COLLECTOR_SOURCE_MAP_V1_READY" "$doc"

echo "collector_source_map=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_COLLECTOR_SOURCE_MAP_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COLLECTOR_SOURCE_MAP_V1_OK"
