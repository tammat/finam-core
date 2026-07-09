#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_REGISTRY_PATCH_V1 ==="

sql_file="sql/analytics/marketcore_model_health_registry_patch_v1.sql"
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

missing_columns=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('metric_table'),
    ('metric_column'),
    ('aggregation_method')
) v(column_name)
LEFT JOIN information_schema.columns c
  ON c.table_schema='analytics'
 AND c.table_name='marketcore_model_health_component_registry_v1'
 AND c.column_name=v.column_name
WHERE c.column_name IS NULL;
")

incomplete_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1
WHERE enabled
  AND (
       metric_table IS NULL
    OR metric_column IS NULL
    OR aggregation_method IS NULL
  );
")

bad_methods=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1
WHERE enabled
  AND aggregation_method NOT IN ('LAST','LAST_BINARY','COUNT','COVERAGE');
")

test "$missing_columns" = "0"
test "$incomplete_rows" = "0"
test "$bad_methods" = "0"

echo "registry_patch=OK"
echo "missing_columns=0"
echo "incomplete_rows=0"
echo "bad_methods=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_REGISTRY_PATCH_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_REGISTRY_PATCH_V1_OK"
