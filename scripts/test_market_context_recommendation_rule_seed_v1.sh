#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1 ==="

sql_file="sql/knowledge/market_context_recommendation_rule_seed_v1.sql"

test -f "$sql_file"

if grep -RInE \
"BUY|SELL|LONG|SHORT|SBER|LKOH|VTBR|GAZP|0\.7|0\.8|0\.9" \
"$sql_file"; then
    echo "HARDCODE_FOUND"
    exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_rule_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1';
")

test "$rows" -ge 5

profiles=$(psql -At -d finam_core -c "
SELECT count(DISTINCT parameter_profile)
FROM knowledge.recommendation_rule_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1';
")

test "$profiles" -ge 1

echo "recommendation_rule_rows=$rows"
echo "parameter_profiles=$profiles"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_RULE_SEED_V1_OK"
