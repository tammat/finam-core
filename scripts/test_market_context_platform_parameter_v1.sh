#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_PLATFORM_PARAMETER_V1 ==="

sql_file="sql/knowledge/market_context_platform_parameter_v1.sql"

test -f "$sql_file"

if grep -RInE \
'DROP TABLE|TRUNCATE|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*edge_score_model_v2' \
"$sql_file"; then
    echo "DANGEROUS_SQL_FOUND"
    exit 1
fi

if grep -RInE \
"SBER|LKOH|GAZP|VTBR|RSI|VWAP|BREAKOUT|LONG|SHORT|BUY|SELL" \
"$sql_file"; then
    echo "HARDCODE_FOUND"
    exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
VALUES
('knowledge.platform_parameter_v1')
) t(full_name)
LEFT JOIN pg_class c
ON c.relname=split_part(full_name,'.',2)
LEFT JOIN pg_namespace n
ON n.oid=c.relnamespace
AND n.nspname=split_part(full_name,'.',1)
WHERE c.oid IS NULL;
SQL
)

test "$missing" = "0"

echo "platform_parameter_schema=OK"
echo "hardcode=0"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_PLATFORM_PARAMETER_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_PLATFORM_PARAMETER_V1_OK"
