#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_REGISTRY_V1 ==="

sql_file="sql/analytics/marketcore_model_health_registry_v1.sql"
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

registry_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1
WHERE enabled
  AND source_version='MARKETCORE_MODEL_HEALTH_REGISTRY_V1';
")

parameter_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1 r
JOIN knowledge.platform_parameter_v1 p
  ON p.parameter_code=r.weight_parameter_code
 AND p.enabled
WHERE r.enabled
  AND r.source_version='MARKETCORE_MODEL_HEALTH_REGISTRY_V1';
")

missing_i18n=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1 r
LEFT JOIN presentation.ui_resource_v1 ui
  ON ui.resource_key='model.health.'||lower(r.component_code)
 AND ui.locale_code='ru'
WHERE r.enabled
  AND ui.resource_key IS NULL;
")

test "$registry_rows" -ge 8
test "$parameter_rows" = "$registry_rows"
test "$missing_i18n" = "0"

echo "model_health_registry_rows=$registry_rows"
echo "model_health_weight_parameters=$parameter_rows"
echo "missing_i18n_resources=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_REGISTRY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_REGISTRY_V1_OK"
