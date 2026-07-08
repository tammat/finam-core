#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1 ==="

sql_files=(
  sql/knowledge/recommendation_execution_context_schema_v1.sql
  sql/knowledge/recommendation_execution_context_direction_seed_v1.sql
)

for f in "${sql_files[@]}"; do
  test -f "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE' "${sql_files[@]}"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE 'BUY|SELL|LONG|SHORT|SBER|LKOH|VTBR|GAZP' "${sql_files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f sql/knowledge/recommendation_execution_context_schema_v1.sql
psql -d finam_core -v ON_ERROR_STOP=1 -f sql/knowledge/recommendation_execution_context_direction_seed_v1.sql

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('knowledge.recommendation_direction_v1'),
    ('knowledge.recommendation_execution_context_v1')
) t(full_name)
LEFT JOIN pg_class c
  ON c.relname=split_part(full_name,'.',2)
LEFT JOIN pg_namespace n
  ON n.oid=c.relnamespace
 AND n.nspname=split_part(full_name,'.',1)
WHERE c.oid IS NULL;
")

test "$missing" = "0"

direction_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_direction_v1
WHERE source_version='RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1'
  AND enabled;
")

test "$direction_rows" -ge 1

unsafe_defaults=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='knowledge'
  AND table_name='recommendation_execution_context_v1'
  AND column_name IN ('execution_allowed','runtime_allowed','micro_live_allowed')
  AND column_default <> '0';
")

test "$unsafe_defaults" = "0"

echo "execution_context_schema=OK"
echo "direction_rows=$direction_rows"
echo "hardcode=0"
echo "execution_allowed_default=0"
echo "runtime_allowed_default=0"
echo "micro_live_allowed_default=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_EXECUTION_CONTEXT_SCHEMA_V1_OK"
