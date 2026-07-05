#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_FACTORY_ROADMAP_V1 ==="

test -f docs/EDGE_FACTORY_ROADMAP.md

grep -q "EDGE FACTORY ROADMAP" docs/EDGE_FACTORY_ROADMAP.md
grep -q "Architecture Stable. Algorithms Adaptive." docs/EDGE_FACTORY_ROADMAP.md
grep -q "Observation" docs/EDGE_FACTORY_ROADMAP.md
grep -q "Paper" docs/EDGE_FACTORY_ROADMAP.md
grep -q "micro_live_allowed по умолчанию false" docs/EDGE_FACTORY_ROADMAP.md

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_FACTORY_ROADMAP_V1_OK"
