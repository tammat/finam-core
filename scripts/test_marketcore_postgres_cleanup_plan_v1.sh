#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_POSTGRES_CLEANUP_PLAN_V1 ==="

mkdir -p reports

plan="reports/postgres_cleanup_plan_v1.txt"

{
echo "=== MARKETCORE POSTGRES CLEANUP PLAN V1 ==="
echo "generated_at=$(date -Is)"
echo
echo "MODE: DRY_RUN_ONLY"
echo

echo "=== CANDIDATE EMPTY TABLES ==="
psql -d finam_core -c "
SELECT schemaname, relname AS table_name, n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup = 0
ORDER BY schemaname, relname;
"

echo
echo "=== CANDIDATE DEAD-TUPLE TABLES FOR VACUUM ==="
psql -d finam_core -c "
SELECT schemaname,
       relname AS table_name,
       n_live_tup,
       n_dead_tup,
       round((n_dead_tup::numeric / greatest(n_live_tup,1)) * 100, 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
"

echo
echo "=== CANDIDATE TECHNICAL TABLES BY NAME REVIEW ONLY ==="
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

echo
echo "=== SAFE ACTIONS PROPOSED ==="
echo "1. VACUUM ANALYZE candidate tables with high dead tuples."
echo "2. Review empty technical tables manually."
echo "3. Do not delete research/shadow/edge history."
echo "4. Do not drop tables in this stage."
echo "5. Prepare explicit allowlist before any destructive cleanup."

} > "$plan"

test -s "$plan"

if grep -RInE 'DROP TABLE|TRUNCATE|DELETE FROM' scripts/test_marketcore_postgres_cleanup_plan_v1.sh | grep -v "grep -RInE"; then
  echo "DESTRUCTIVE_SQL_FOUND_IN_CLEANUP_PLAN"
  exit 1
fi

echo "plan=$plan"
echo "cleanup_mode=dry_run_only"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_POSTGRES_CLEANUP_PLAN_V1_READY"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_CLEANUP_PLAN_V1_OK"
