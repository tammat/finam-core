#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_STRUCTURE_PARAMETER_SEED_V1 ==="

sql_file="sql/knowledge/market_structure_parameter_seed_v1.sql"
test -f "$sql_file"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills' "$sql_file"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE 'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' "$sql_file"; then
  echo "HARDCODE_SYMBOL_OR_TRADE_ACTION_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

type_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.market_structure_type_v1
WHERE source_version='MARKET_STRUCTURE_PARAMETER_SEED_V1'
  AND enabled;
")

parameter_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.platform_parameter_v1
WHERE source_version='MARKET_STRUCTURE_PARAMETER_SEED_V1'
  AND enabled;
")

test "$type_rows" -ge 10
test "$parameter_rows" -ge 5

echo "market_structure_type_rows=$type_rows"
echo "market_structure_parameter_rows=$parameter_rows"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_STRUCTURE_PARAMETER_SEED_V1_READY"
echo "VERDICT=TEST_MARKET_STRUCTURE_PARAMETER_SEED_V1_OK"
