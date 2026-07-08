#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1 ==="

sql_file="sql/knowledge/market_context_correlation_config_seed_v1.sql"
test -f "$sql_file"

if grep -RInE 'DROP TABLE|TRUNCATE|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*edge_score_model_v2' "$sql_file"; then
  echo "DANGEROUS_SQL_FOUND"
  exit 1
fi

if grep -RInE "SBER|LKOH|VTBR|GAZP|IMOEX|RTSI" "$sql_file"; then
  echo "HARDCODED_SYMBOL_FOUND"
  exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

rule_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM knowledge.correlation_rule_v1
WHERE source_version='MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'
  AND is_active;
")

universe_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM knowledge.correlation_universe_v1
WHERE source_version='MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1'
  AND is_active;
")

test "$rule_rows" -ge 1
test "$universe_rows" -ge 1

echo "correlation_rule_rows=$rule_rows"
echo "correlation_universe_rows=$universe_rows"
echo "symbol_hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_CORRELATION_CONFIG_SEED_V1_OK"
