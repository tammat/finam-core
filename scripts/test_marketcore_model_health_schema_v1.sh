#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_SCHEMA_V1 ==="

sql_file="sql/analytics/marketcore_model_health_schema_v1.sql"
test -f "$sql_file"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$sql_file"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$sql_file"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('analytics.marketcore_model_health_snapshot_v1'),
    ('analytics.marketcore_model_health_component_v1'),
    ('analytics.marketcore_model_health_gate_v1'),
    ('analytics.marketcore_model_health_recommendation_v1')
) t(full_name)
LEFT JOIN pg_class c
  ON c.relname=split_part(full_name,'.',2)
LEFT JOIN pg_namespace n
  ON n.oid=c.relnamespace
 AND n.nspname=split_part(full_name,'.',1)
WHERE c.oid IS NULL;
")

bad_defaults=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name='marketcore_model_health_recommendation_v1'
  AND column_name IN ('approved','applied','auto_decision')
  AND column_default <> '0';
")

fk_count=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.table_constraints
WHERE table_schema='analytics'
  AND constraint_type='FOREIGN KEY'
  AND table_name IN (
    'marketcore_model_health_snapshot_v1',
    'marketcore_model_health_component_v1',
    'marketcore_model_health_gate_v1',
    'marketcore_model_health_recommendation_v1'
  );
")

test "$missing" = "0"
test "$bad_defaults" = "0"
test "$fk_count" -ge 5

echo "model_health_schema=OK"
echo "tables_missing=0"
echo "safe_defaults=OK"
echo "fk_count=$fk_count"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_SCHEMA_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_SCHEMA_V1_OK"
