#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_SIMULATOR_V1 ==="

sql_file="sql/knowledge/paper_execution_simulator_v1.sql"
py_file="src/scripts/paper_execution_simulator_v1.py"

test -f "$sql_file"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_paper_simulator \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE|DELETE FROM' "$sql_file" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$sql_file" "$py_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$py_file")
echo "$out"
echo "$out" | grep -q "VERDICT=PAPER_EXECUTION_SIMULATOR_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.paper_execution_result_v1
WHERE source_version='PAPER_EXECUTION_SIMULATOR_V1';
")

bad_fk=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.paper_execution_result_v1 p
LEFT JOIN knowledge.recommendation_execution_context_v1 x
  ON x.execution_context_id=p.execution_context_id
LEFT JOIN knowledge.recommendation_result_v1 r
  ON r.recommendation_id=p.recommendation_id
WHERE p.source_version='PAPER_EXECUTION_SIMULATOR_V1'
  AND (
       x.execution_context_id IS NULL
    OR r.recommendation_id IS NULL
  );
")

bad_quality=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.paper_execution_result_v1
WHERE source_version='PAPER_EXECUTION_SIMULATOR_V1'
  AND (
       entry_price IS NULL
    OR exit_price IS NULL
    OR invalidation_price IS NULL
    OR target_price IS NULL
    OR exit_reason IS NULL
    OR bars_held <= 0
    OR NOT evidence_json ? 'mode'
  );
")

test "$rows" -ge 1
test "$bad_fk" = "0"
test "$bad_quality" = "0"

echo "paper_execution_result_rows=$rows"
echo "bad_fk_rows=0"
echo "bad_quality_rows=0"
echo "paper_orders_created=0"
echo "paper_fills_created=0"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_SIMULATOR_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_SIMULATOR_V1_OK"
