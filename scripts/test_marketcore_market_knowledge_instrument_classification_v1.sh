#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1 ==="

file="src/scripts/market_knowledge_instrument_classification_v1.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_instrument_classification \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DELETE FROM|DROP TABLE|TRUNCATE' "$file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

out=$(PYTHONPYCACHEPREFIX=/tmp/finam_pycache_mk_instrument_classification PYTHONPATH=src python "$file")
echo "$out"

echo "$out" | grep -q "VERDICT=MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1_READY"
echo "$out" | grep -q "edge_score_v2_changed=0"
echo "$out" | grep -q "runtime_changed=0"
echo "$out" | grep -q "execution_changed=0"
echo "$out" | grep -q "orders_changed=0"
echo "$out" | grep -q "fills_changed=0"
echo "$out" | grep -q "micro_live_allowed=0"

classified=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.instrument_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1';
")

if [ "$classified" -lt 1 ]; then
  echo "NO_CLASSIFIED_INSTRUMENTS"
  exit 1
fi

missing_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.instrument_v1
WHERE source_version='MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1'
  AND (exchange_id IS NULL OR asset_class_id IS NULL OR sector_id IS NULL);
")

if [ "$missing_fk" != "0" ]; then
  echo "MISSING_CLASSIFICATION_FK=$missing_fk"
  exit 1
fi

echo "classified_instruments=$classified"
echo "missing_fk=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1_OK"
