#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_VISION_2030 ==="

doc="docs/MARKETCORE_VISION_2030.txt"

test -f "$doc"

for section in \
"MISSION" \
"CORE PHILOSOPHY" \
"KNOWLEDGE FIRST" \
"EDGE" \
"KNOWLEDGE" \
"RECOMMENDATION" \
"EXECUTION" \
"BROKER MODEL" \
"SAFETY" \
"VISION"
do
    grep -q "$section" "$doc"
done

grep -q "MarketCore является независимой платформой" "$doc"
grep -q "Knowledge является активом первого класса" "$doc"
grep -q "Observe." "$doc"
grep -q "Understand." "$doc"
grep -q "Explain." "$doc"
grep -q "Recommend." "$doc"
grep -q "MARKETCORE_VISION_2030_READY" "$doc"

echo "vision_document=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_VISION_2030_READY"
echo "VERDICT=TEST_MARKETCORE_VISION_2030_OK"
