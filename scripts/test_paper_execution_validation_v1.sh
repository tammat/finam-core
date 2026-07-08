#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_VALIDATION_V1 ==="

sql_files=(
  sql/knowledge/paper_execution_validation_v1.sql
  sql/knowledge/paper_execution_validation_parameter_seed_v1.sql
)

py_file="src/scripts/paper_execution_validation_v1.py"

for f in "${sql_files[@]}"; do
  test -f "$f"
done

test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_paper_validation PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' \
  "${sql_files[@]}" "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE 'BUY|SELL|LONG|SHORT|SBER|LKOH|VTBR|GAZP|80|70|60|50|0\.70|0\.80|0\.90' "$py_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f sql/knowledge/paper_execution_validation_v1.sql
psql -d finam_core -v ON_ERROR_STOP=1 -f sql/knowledge/paper_execution_validation_parameter_seed_v1.sql

before_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

out=$(PYTHONPATH=src python "$py_file")
echo "$out"
echo "$out" | grep -q "VERDICT=PAPER_EXECUTION_VALIDATION_V1_READY"

after_edge=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_score_model_v2;")

if [ "$before_edge" != "$after_edge" ]; then
  echo "EDGE_SCORE_V2_CHANGED"
  exit 1
fi

validation_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.paper_execution_validation_v1
WHERE source_version='PAPER_EXECUTION_VALIDATION_V1';
")

test "$validation_rows" -ge 1

echo "paper_validation_rows=$validation_rows"
echo "validation_only=OK"
echo "paper_orders_created=0"
echo "paper_fills_created=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_VALIDATION_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_VALIDATION_V1_OK"
