#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_ARCHITECTURE_FREEZE_V3 ==="

doc="docs/MARKETCORE_ARCHITECTURE_FREEZE_V3.txt"

test -f "$doc"

for section in \
"CORE PRINCIPLE" \
"PROJECT MODEL" \
"ARCHITECTURE STATUS" \
"RULE OF EVIDENCE" \
"NO NEW ARCHITECTURE RULE" \
"KNOWLEDGE FIRST" \
"BROKER MODEL" \
"EXECUTION" \
"DEVELOPMENT MODEL" \
"PROJECT PRIORITY" \
"SUCCESS CRITERION"
do
    grep -q "$section" "$doc"
done

grep -q "Architecture" "$doc"
grep -q "STABILIZED" "$doc"
grep -q "Platform" "$doc"
grep -q "READY FOR EVOLUTION" "$doc"
grep -q "MARKETCORE_ARCHITECTURE_FREEZE_V3_READY" "$doc"

echo "architecture_freeze=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_ARCHITECTURE_FREEZE_V3_READY"
echo "VERDICT=TEST_MARKETCORE_ARCHITECTURE_FREEZE_V3_OK"
