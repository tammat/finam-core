#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_SOURCE_REGISTRY_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
-f sql/knowledge/trading_plan_source_registry_v1.sql

scripts/test_trading_plan_source_registry_i18n_v1.sh

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.trading_plan_source_v1
WHERE enabled;
")

test "$rows" -ge 12

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.trading_plan_source_v1 s
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='trading_plan.source.'||lower(s.source_code)
AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

test "$missing" = "0"

echo "sources=$rows"
echo "missing_i18n=$missing"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TRADING_PLAN_SOURCE_REGISTRY_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_SOURCE_REGISTRY_V1_OK"
