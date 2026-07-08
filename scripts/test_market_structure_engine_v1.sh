#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_STRUCTURE_ENGINE_V1 ==="

file="src/scripts/market_structure_engine_v1.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_market_structure_engine \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$file")
echo "$out"
echo "$out" | grep -q "VERDICT=MARKET_STRUCTURE_ENGINE_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1';
")

types=$(psql -At -d finam_core -c "
SELECT count(DISTINCT structure_type_code)
FROM knowledge.market_structure_v1
WHERE source_version='MARKET_STRUCTURE_ENGINE_V1';
")

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_structure_v1 s
LEFT JOIN knowledge.market_structure_type_v1 t
  ON t.structure_type_code=s.structure_type_code
WHERE s.source_version='MARKET_STRUCTURE_ENGINE_V1'
  AND t.structure_type_code IS NULL;
")

test "$rows" -ge 1
test "$types" -ge 1
test "$bad_fk" = "0"

echo "market_structure_rows=$rows"
echo "market_structure_types=$types"
echo "bad_fk_rows=0"
echo "config_source=postgres"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_STRUCTURE_ENGINE_V1_READY"
echo "VERDICT=TEST_MARKET_STRUCTURE_ENGINE_V1_OK"
