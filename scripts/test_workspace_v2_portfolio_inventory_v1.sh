#!/usr/bin/env bash
set -euo pipefail

echo "======================================================"
echo "WORKSPACE_V2_PORTFOLIO_V2_INVENTORY"
echo "======================================================"

mkdir -p reports

report="reports/workspace_v2_portfolio_inventory_v1.txt"

{
echo "=== GENERATED ==="
date -Is

echo
echo "======================================================"
echo "1. PYTHON MODULES"
echo "======================================================"

find src -type f | \
grep -Ei "portfolio|capital|position|equity|risk|pnl" | \
sort || true

echo
echo "======================================================"
echo "2. PRESENTATION MODULES"
echo "======================================================"

find src/marketcore/presentation -type f | \
grep -Ei "portfolio|capital|position|equity|risk|pnl" | \
sort || true

echo
echo "======================================================"
echo "3. SQL FILES"
echo "======================================================"

find sql -type f | \
grep -Ei "portfolio|capital|position|equity|risk|pnl" | \
sort || true

echo
echo "======================================================"
echo "4. DATABASE TABLES"
echo "======================================================"

psql -d finam_core -P pager=off <<'SQL'
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema IN
(
'portfolio',
'analytics',
'knowledge',
'presentation',
'public'
)
AND
(
       lower(table_name) LIKE '%portfolio%'
    OR lower(table_name) LIKE '%capital%'
    OR lower(table_name) LIKE '%position%'
    OR lower(table_name) LIKE '%equity%'
    OR lower(table_name) LIKE '%risk%'
    OR lower(table_name) LIKE '%pnl%'
)
ORDER BY 1,2;
SQL

echo
echo "======================================================"
echo "5. PORTFOLIO COLUMNS"
echo "======================================================"

psql -d finam_core -P pager=off <<'SQL'
SELECT
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema IN
(
'portfolio',
'analytics',
'knowledge',
'presentation',
'public'
)
AND
(
       lower(table_name) LIKE '%portfolio%'
    OR lower(table_name) LIKE '%capital%'
    OR lower(table_name) LIKE '%position%'
    OR lower(table_name) LIKE '%equity%'
    OR lower(table_name) LIKE '%risk%'
    OR lower(table_name) LIKE '%pnl%'
)
ORDER BY
table_schema,
table_name,
ordinal_position;
SQL

echo
echo "======================================================"
echo "6. EXISTING PORTFOLIO ROUTES"
echo "======================================================"

grep -RIn "portfolio" src/marketcore/presentation || true

echo
echo "======================================================"
echo "7. INVENTORY SUMMARY"
echo "======================================================"

echo "mode=inventory_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_V2_INVENTORY_READY"

} | tee "$report"

grep -q "WORKSPACE_V2_PORTFOLIO_V2_INVENTORY_READY" "$report"

echo
echo "report=$report"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_PORTFOLIO_V2_INVENTORY_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_V2_INVENTORY_OK"
