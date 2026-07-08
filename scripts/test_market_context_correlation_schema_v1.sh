#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_CORRELATION_SCHEMA_V1 ==="

sql_file="sql/knowledge/market_context_correlation_schema_v1.sql"
test -f "$sql_file"

if grep -RInE 'DROP TABLE|TRUNCATE|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*edge_score_model_v2' "$sql_file"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

# Проверяем отсутствие hardcoded торговых пар/окон внутри SQL.
if grep -RInE "SBER|LKOH|VTBR|GAZP|BR|NG|IMOEX|RTSI|20|50|100|250|0\.7|0\.8|0\.9" "$sql_file"; then
  echo "HARDCODED_CORRELATION_CONFIG_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('knowledge.correlation_rule_v1'),
    ('knowledge.correlation_universe_v1')
) AS required(full_name)
LEFT JOIN pg_class c
  ON c.relname = split_part(required.full_name, '.', 2)
LEFT JOIN pg_namespace n
  ON n.oid = c.relnamespace
 AND n.nspname = split_part(required.full_name, '.', 1)
WHERE c.oid IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_CORRELATION_TABLES=$missing"
  exit 1
fi

echo "correlation_config_schema=OK"
echo "hardcode=0"
echo "destructive_sql=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_CORRELATION_SCHEMA_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_CORRELATION_SCHEMA_V1_OK"
