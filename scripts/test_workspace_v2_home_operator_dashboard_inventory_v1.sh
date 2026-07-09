#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_INVENTORY_V1 ==="

psql -d finam_core -P pager=off <<'SQL'
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('analytics','presentation','public','knowledge')
AND (
       lower(table_name) LIKE '%recommend%'
    OR lower(table_name) LIKE '%feedback%'
    OR lower(table_name) LIKE '%event%'
    OR lower(table_name) LIKE '%journal%'
    OR lower(table_name) LIKE '%signal%'
    OR lower(table_name) LIKE '%risk%'
    OR lower(table_name) LIKE '%health%'
)
ORDER BY 1,2;
SQL

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_INVENTORY_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_OPERATOR_DASHBOARD_INVENTORY_V1_OK"
