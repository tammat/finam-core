#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_STATUS_DYNAMIC_INVENTORY_V1 ==="

psql -d finam_core -P pager=off <<'SQL'
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('analytics','presentation','public','knowledge')
AND (
       lower(table_name) LIKE '%paper%'
    OR lower(table_name) LIKE '%probe%'
    OR lower(table_name) LIKE '%shadow%'
    OR lower(table_name) LIKE '%runtime%'
    OR lower(table_name) LIKE '%research%'
    OR lower(table_name) LIKE '%edge%'
    OR lower(table_name) LIKE '%portfolio%'
)
ORDER BY 1,2;
SQL

echo "VERDICT=WORKSPACE_V2_HOME_STATUS_DYNAMIC_INVENTORY_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_STATUS_DYNAMIC_INVENTORY_V1_OK"
