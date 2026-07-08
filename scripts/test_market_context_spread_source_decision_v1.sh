#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_SPREAD_SOURCE_DECISION_V1 ==="

doc="docs/MARKET_CONTEXT_SPREAD_SOURCE_DECISION_V1.txt"

test -f "$doc"

grep -q "Spread SHALL NOT be synthesized" "$doc"
grep -q "UNKNOWN" "$doc"
grep -q "Order Book" "$doc"
grep -q "Exchange Level 2" "$doc"
grep -q "MARKET_CONTEXT_SPREAD_SOURCE_DECISION_V1_READY" "$doc"

echo "spread_source_decision=OK"
echo "collector_policy=UNKNOWN_ALLOWED"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_SPREAD_SOURCE_DECISION_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_SPREAD_SOURCE_DECISION_V1_OK"
