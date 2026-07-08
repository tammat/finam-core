#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_DATA_CATALOG_RECONCILIATION_V1 ==="

mkdir -p reports

report="reports/data_catalog_reconciliation_v1.txt"

{
echo "======================================================"
echo "MARKETCORE DATA CATALOG RECONCILIATION"
echo "======================================================"
echo
echo "generated_at=$(date -Is)"
echo

echo "================ SCHEMAS ================"
psql -d finam_core -P pager=off -c "
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog','information_schema')
ORDER BY schema_name;
"

echo
echo "================ TABLES ================"
psql -d finam_core -P pager=off -c "
SELECT
    schemaname,
    relname,
    n_live_tup,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
ORDER BY schemaname, relname;
"

echo
echo "================ VIEWS ================"
psql -d finam_core -P pager=off -c "
SELECT table_schema,
       table_name
FROM information_schema.views
WHERE table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY table_schema, table_name;
"

echo
echo "================ MATERIALIZED VIEWS ================"
psql -d finam_core -P pager=off -c "
SELECT schemaname,
       matviewname
FROM pg_matviews
ORDER BY schemaname, matviewname;
"

echo
echo "================ KNOWLEDGE TABLES ================"
psql -d finam_core -P pager=off -c "
SELECT
    table_name
FROM information_schema.tables
WHERE table_schema='knowledge'
ORDER BY table_name;
"

echo
echo "================ ANALYTICS TABLES ================"
psql -d finam_core -P pager=off -c "
SELECT
    table_name
FROM information_schema.tables
WHERE table_schema='analytics'
ORDER BY table_name;
"

echo
echo "================ MARKET DATA TABLES ================"
psql -d finam_core -P pager=off -c "
SELECT
    schemaname,
    relname
FROM pg_stat_user_tables
WHERE
      relname ILIKE '%bar%'
   OR relname ILIKE '%market%'
   OR relname ILIKE '%tick%'
ORDER BY schemaname, relname;
"

echo
echo "================ POSSIBLE INDEX DATA ================"
psql -d finam_core -P pager=off -c "
SELECT DISTINCT symbol
FROM analytics.edge_score_model_v2
ORDER BY symbol;
"

echo
echo "================ DATA GAPS ================"
echo "To be reviewed manually:"
echo "- IMOEX"
echo "- RTSI"
echo "- Sector indices"
echo "- Brent spot"
echo "- Natural Gas spot"
echo "- USD/RUB"
echo "- CNY/RUB"
echo "- Macro calendar"
echo "- Dividends"
echo "- Expiration calendar"

} > "$report"

test -s "$report"

echo "report=$report"
echo "mode=read_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_DATA_CATALOG_RECONCILIATION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_DATA_CATALOG_RECONCILIATION_V1_OK"
