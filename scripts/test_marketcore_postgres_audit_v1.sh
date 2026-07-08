#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_POSTGRES_AUDIT_V1 ==="

mkdir -p reports

report="reports/postgres_audit_v1.txt"

{
echo "=== MARKETCORE POSTGRES AUDIT V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== DATABASE SIZE ==="
psql -d finam_core -c "
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
"

echo
echo "=== SCHEMA SIZES ==="
psql -d finam_core -c "
SELECT schemaname,
       pg_size_pretty(sum(pg_total_relation_size(relid))::bigint) AS total_size
FROM pg_stat_user_tables
GROUP BY schemaname
ORDER BY sum(pg_total_relation_size(relid)) DESC;
"

echo
echo "=== TABLE ROW COUNTS APPROX ==="
psql -d finam_core -c "
SELECT schemaname,
       relname AS table_name,
       n_live_tup,
       n_dead_tup,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC, n_live_tup DESC;
"

echo
echo "=== POSSIBLE STALE TABLES ==="
psql -d finam_core -c "
SELECT schemaname,
       relname AS table_name,
       n_live_tup,
       n_dead_tup,
       last_vacuum,
       last_autovacuum,
       last_analyze,
       last_autoanalyze
FROM pg_stat_user_tables
WHERE n_live_tup = 0 OR n_dead_tup > n_live_tup
ORDER BY n_dead_tup DESC, n_live_tup ASC;
"

echo
echo "=== LARGEST INDEXES ==="
psql -d finam_core -c "
SELECT schemaname,
       relname AS table_name,
       indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
       idx_scan
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 50;
"

echo
echo "=== TABLES WITHOUT RECENT ANALYZE ==="
psql -d finam_core -c "
SELECT schemaname,
       relname AS table_name,
       n_live_tup,
       last_analyze,
       last_autoanalyze
FROM pg_stat_user_tables
WHERE last_analyze IS NULL AND last_autoanalyze IS NULL
ORDER BY n_live_tup DESC;
"

echo
echo "=== DUPLICATE-LIKE TABLE NAMES ==="
psql -d finam_core -c "
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
  AND (
    table_name ILIKE '%tmp%'
    OR table_name ILIKE '%backup%'
    OR table_name ILIKE '%old%'
    OR table_name ILIKE '%test%'
    OR table_name ILIKE '%copy%'
    OR table_name ILIKE '%staging%'
  )
ORDER BY table_schema, table_name;
"

} > "$report"

test -s "$report"

echo "report=$report"
echo "audit_mode=read_only"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_AUDIT_V1_OK"
