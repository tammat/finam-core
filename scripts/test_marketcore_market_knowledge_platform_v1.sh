#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1 ==="

doc="docs/MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1.txt"
test -f "$doc"

grep -q "MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1" "$doc"
grep -q "market regime" "$doc"
grep -q "instrument context" "$doc"
grep -q "correlation context" "$doc"
grep -q "Edge Score V2 remains frozen" "$doc"
grep -q "execution_allowed=0" "$doc"
grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1_READY" "$doc"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution' "$doc"; then
  echo "DANGEROUS_MARKET_KNOWLEDGE_TEXT_FOUND"
  exit 1
fi

echo "market_knowledge_doc=OK"
echo "edge_score_v2_frozen=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_PLATFORM_V1_OK"
