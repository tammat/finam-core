#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_EXECUTION_CONTEXT_REQUIREMENTS_V1 ==="

doc="docs/RECOMMENDATION_EXECUTION_CONTEXT_REQUIREMENTS_V1.txt"
test -f "$doc"

for section in \
  "MANDATORY EXECUTION CONTEXT" \
  "NON GOALS" \
  "SAFETY" \
  "NEXT STEP" \
  "VERDICT"
do
  grep -q "$section" "$doc"
done

for field in \
  "direction_code" \
  "entry_price" \
  "invalidation_price" \
  "target_price" \
  "horizon_bars" \
  "risk_unit" \
  "source_context_id" \
  "source_edge_context_id"
do
  grep -q "$field" "$doc"
done

grep -q "This document does NOT enable execution" "$doc"
grep -q "orders_changed=0" "$doc"
grep -q "micro_live_allowed=0" "$doc"
grep -q "RECOMMENDATION_EXECUTION_CONTEXT_REQUIREMENTS_V1_READY" "$doc"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE' "$doc"; then
  echo "DANGEROUS_CONTENT_FOUND"
  exit 1
fi

echo "execution_context_requirements=OK"
echo "mode=document_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_REQUIREMENTS_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_EXECUTION_CONTEXT_REQUIREMENTS_V1_OK"
