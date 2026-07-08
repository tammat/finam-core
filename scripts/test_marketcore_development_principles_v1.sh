#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_DEVELOPMENT_PRINCIPLES_V1 ==="

doc="docs/MARKETCORE_DEVELOPMENT_PRINCIPLES_V1.txt"

test -f "$doc"

for section in \
  "ARCHITECTURE FIRST" \
  "LAYER SEPARATION" \
  "ZERO HTML POLICY" \
  "I18N FIRST" \
  "SAFETY FIRST" \
  "POSTGRESQL ONLY" \
  "BASH TEST ONLY" \
  "CHECKPOINT DISCIPLINE" \
  "BROKER SEPARATION" \
  "WIDGET FIRST RULE" \
  "ROUTE HEALTHCHECK" \
  "MOBILE FIRST FOR OPERATOR UI"
do
  grep -q "$section" "$doc"
done

grep -q "MARKETCORE_DEVELOPMENT_PRINCIPLES_V1_READY" "$doc"
grep -q "PostgreSQL является единственным допустимым хранилищем" "$doc"
grep -q "SQLite запрещен" "$doc"
grep -q "pytest и unittest не используются" "$doc"
grep -q "MarketCore является платформой" "$doc"
grep -q "Finam является broker adapter" "$doc"

echo "development_principles=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_DEVELOPMENT_PRINCIPLES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_DEVELOPMENT_PRINCIPLES_V1_OK"
