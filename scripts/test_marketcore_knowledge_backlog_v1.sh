#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_KNOWLEDGE_BACKLOG_V1 ==="

doc="docs/MARKETCORE_KNOWLEDGE_BACKLOG_V1.txt"
test -f "$doc"

grep -q "Evidence Before Complexity" "$doc"
grep -q "MARKET STRUCTURE ENGINE" "$doc"
grep -q "Fibonacci Retracement" "$doc"
grep -q "Fibonacci Extension" "$doc"
grep -q "VOLUME STRUCTURE ENGINE" "$doc"
grep -q "ORDER FLOW / MICROSTRUCTURE ENGINE" "$doc"
grep -q "MARKET MEMORY" "$doc"
grep -q "KNOWLEDGE ROI" "$doc"
grep -q "MARKETCORE_KNOWLEDGE_BACKLOG_V1_READY" "$doc"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$doc"; then
  echo "DANGEROUS_CONTENT_FOUND"
  exit 1
fi

echo "knowledge_backlog=OK"
echo "mode=document_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_KNOWLEDGE_BACKLOG_V1_READY"
echo "VERDICT=TEST_MARKETCORE_KNOWLEDGE_BACKLOG_V1_OK"
