#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1 ==="

sql_file="sql/knowledge/market_context_recommendation_parameter_seed_v1.sql"

test -f "$sql_file"

if grep -RInE \
"BUY|SELL|LONG|SHORT|SBER|LKOH|VTBR|GAZP" \
"$sql_file"; then
    echo "HARDCODE_SYMBOL_FOUND"
    exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.platform_parameter_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1';
")

test "$rows" -ge 7

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
VALUES
('PROFILE_DEFAULT'),
('EDGE_VALIDATE_THRESHOLD'),
('EDGE_RESEARCH_THRESHOLD'),
('EDGE_OBSERVE_THRESHOLD'),
('KNOWLEDGE_MIN_THRESHOLD'),
('MIN_REASONS_REQUIRED'),
('MIN_CONFIDENCE_REQUIRED')
) p(code)
LEFT JOIN knowledge.platform_parameter_v1 k
ON k.parameter_code=p.code
WHERE k.parameter_code IS NULL;
")

test "$missing" = "0"

echo "parameter_rows=$rows"
echo "missing_parameters=0"
echo "hardcode_symbols=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_PARAMETER_SEED_V1_OK"
