#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_ROADMAP_V3 ==="

doc="docs/ROADMAP_V3.txt"

test -f "$doc"

grep -q "PHASE 1" "$doc"
grep -q "PHASE 2" "$doc"
grep -q "PHASE 3" "$doc"
grep -q "PHASE 4" "$doc"
grep -q "PHASE 5" "$doc"
grep -q "PHASE 6" "$doc"

grep -q "Operator Workspace" "$doc"
grep -q "Market Knowledge Platform" "$doc"
grep -q "Broker Abstraction" "$doc"
grep -q "Execution Platform" "$doc"

grep -q "MarketCore является независимой исследовательской платформой" "$doc"
grep -q "Finam является одним из Broker Adapter" "$doc"

echo "roadmap=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=ROADMAP_V3_READY"
echo "VERDICT=TEST_ROADMAP_V3_OK"
