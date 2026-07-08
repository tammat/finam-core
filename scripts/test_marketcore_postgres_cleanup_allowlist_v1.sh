#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_POSTGRES_CLEANUP_ALLOWLIST_V1 ==="

mkdir -p reports

allowlist="reports/postgres_cleanup_allowlist_v1.txt"

{
echo "=== MARKETCORE POSTGRES CLEANUP ALLOWLIST V1 ==="
echo "generated_at=$(date -Is)"
echo
echo "MODE: ALLOWLIST_ONLY"
echo "DELETE_ALLOWED=0"
echo "DROP_ALLOWED=0"
echo "TRUNCATE_ALLOWED=0"
echo

echo "=== VACUUM_ANALYZE_ALLOWLIST ==="
psql -d finam_core -c "
SELECT
    'VACUUM_ANALYZE' AS action_class,
    schemaname,
    relname AS table_name,
    n_live_tup,
    n_dead_tup,
    round((n_dead_tup::numeric / greatest(n_live_tup,1)) * 100, 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
"

echo
echo "=== ANALYZE_ALLOWLIST ==="
psql -d finam_core -c "
SELECT
    'ANALYZE' AS action_class,
    schemaname,
    relname AS table_name,
    n_live_tup,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE last_analyze IS NULL
  AND last_autoanalyze IS NULL
ORDER BY n_live_tup DESC;
"

echo
echo "=== REVIEW_ONLY_EMPTY_TABLES ==="
psql -d finam_core -c "
SELECT
    'REVIEW_EMPTY_TECHNICAL_TABLE' AS action_class,
    schemaname,
    relname AS table_name,
    n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup = 0
ORDER BY schemaname, relname;
"

echo
echo "=== REVIEW_ONLY_TECHNICAL_NAMES ==="
psql -d finam_core -c "
SELECT
    'REVIEW_TMP_BACKUP_OLD_COPY_STAGING_TABLE' AS action_class,
    table_schema,
    table_name
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

echo
echo "=== PRESERVE_PATTERNS ==="
echo "analytics.edge_score%"
echo "analytics.%shadow%"
echo "analytics.%research%"
echo "analytics.%checkpoint%"
echo "orders"
echo "fills"

} > "$allowlist"

test -s "$allowlist"

# В allowlist не должно быть исполняющих destructive SQL-команд.
if grep -E '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution)' "$allowlist"; then
  echo "DESTRUCTIVE_SQL_FOUND_IN_ALLOWLIST_REPORT"
  exit 1
fi

# Скрипт тоже не должен содержать destructive SQL как исполняемую строку.
if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution)' scripts/test_marketcore_postgres_cleanup_allowlist_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND_IN_ALLOWLIST_SCRIPT"
  exit 1
fi

grep -q "MODE: ALLOWLIST_ONLY" "$allowlist"
grep -q "VACUUM_ANALYZE_ALLOWLIST" "$allowlist"
grep -q "ANALYZE_ALLOWLIST" "$allowlist"
grep -q "REVIEW_ONLY_EMPTY_TABLES" "$allowlist"
grep -q "PRESERVE_PATTERNS" "$allowlist"

echo "allowlist=$allowlist"
echo "allowlist_mode=only"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_POSTGRES_CLEANUP_ALLOWLIST_V1_READY"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_CLEANUP_ALLOWLIST_V1_OK"
