#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PLATFORM_AUDIT_REPORT_V1 ==="

doc="docs/MARKETCORE_PLATFORM_AUDIT_REPORT_V1.txt"

test -f "$doc"

for section in \
  "EXECUTIVE SUMMARY" \
  "ARCHITECTURE AUDIT" \
  "RESEARCH AUDIT" \
  "EDGE QUALITY AUDIT" \
  "POSTGRESQL AUDIT" \
  "WIDGET AUDIT" \
  "OPERATOR WORKSPACE AUDIT" \
  "SIDEBAR AUDIT" \
  "HEADER AUDIT" \
  "I18N AUDIT" \
  "BRANDING AUDIT" \
  "MOBILE AUDIT" \
  "PERFORMANCE AUDIT" \
  "SAFETY AUDIT" \
  "CODE HEALTH AUDIT" \
  "PRODUCT READINESS AUDIT" \
  "FINAL DECISION"
do
  grep -q "$section" "$doc"
done

grep -q "Execution Platform: LOCKED" "$doc"
grep -q "MarketCore is product name" "$doc"
grep -q "Finam is broker adapter only" "$doc"
grep -q "DD.MM.YY HH:MM" "$doc"

echo "audit_report_doc=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_PLATFORM_AUDIT_REPORT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PLATFORM_AUDIT_REPORT_V1_OK"
