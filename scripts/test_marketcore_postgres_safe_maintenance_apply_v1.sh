#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_POSTGRES_SAFE_MAINTENANCE_APPLY_V1 ==="

mkdir -p reports

report="reports/postgres_safe_maintenance_apply_v1.txt"

{
echo "=== MARKETCORE POSTGRES SAFE MAINTENANCE APPLY V1 ==="
echo "generated_at=$(date -Is)"
echo "mode=SAFE_MAINTENANCE_ONLY"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo

echo "=== VACUUM_ANALYZE_TARGETS ==="
psql -At -d finam_core -c "
SELECT st.schemaname || '.' || st.relname
FROM pg_stat_user_tables st
JOIN pg_class c ON c.oid = st.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE st.n_dead_tup > 1000
  AND has_schema_privilege(st.schemaname, 'USAGE')
  AND pg_get_userbyid(c.relowner) = current_user
ORDER BY st.n_dead_tup DESC;
"

echo
echo "=== ANALYZE_TARGETS ==="
psql -At -d finam_core -c "
SELECT st.schemaname || '.' || st.relname
FROM pg_stat_user_tables st
JOIN pg_class c ON c.oid = st.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE st.last_analyze IS NULL
  AND st.last_autoanalyze IS NULL
  AND has_schema_privilege(st.schemaname, 'USAGE')
  AND pg_get_userbyid(c.relowner) = current_user
ORDER BY st.n_live_tup DESC;
"
} > "$report"

vacuum_targets=$(psql -At -d finam_core -c "
SELECT st.schemaname || '.' || st.relname
FROM pg_stat_user_tables st
JOIN pg_class c ON c.oid = st.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE st.n_dead_tup > 1000
  AND has_schema_privilege(st.schemaname, 'USAGE')
  AND pg_get_userbyid(c.relowner) = current_user
ORDER BY st.n_dead_tup DESC;
")

analyze_targets=$(psql -At -d finam_core -c "
SELECT st.schemaname || '.' || st.relname
FROM pg_stat_user_tables st
JOIN pg_class c ON c.oid = st.relid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE st.last_analyze IS NULL
  AND st.last_autoanalyze IS NULL
  AND has_schema_privilege(st.schemaname, 'USAGE')
  AND pg_get_userbyid(c.relowner) = current_user
ORDER BY st.n_live_tup DESC;
")

vacuum_count=0
analyze_count=0

while IFS= read -r table_name; do
  [ -n "$table_name" ] || continue
  echo "VACUUM_ANALYZE_APPLY table=$table_name" | tee -a "$report"
  psql -d finam_core -v ON_ERROR_STOP=1 -c "VACUUM ANALYZE $table_name;" >> "$report"
  vacuum_count=$((vacuum_count + 1))
done <<< "$vacuum_targets"

while IFS= read -r table_name; do
  [ -n "$table_name" ] || continue
  echo "ANALYZE_APPLY table=$table_name" | tee -a "$report"
  psql -d finam_core -v ON_ERROR_STOP=1 -c "ANALYZE $table_name;" >> "$report"
  analyze_count=$((analyze_count + 1))
done <<< "$analyze_targets"

if grep -RInE '^[[:space:]]*(DELETE[[:space:]]+FROM|DROP[[:space:]]+TABLE|TRUNCATE[[:space:]]+TABLE|UPDATE[[:space:]]+runtime|UPDATE[[:space:]]+execution)' \
  scripts/test_marketcore_postgres_safe_maintenance_apply_v1.sh; then
  echo "DESTRUCTIVE_SQL_FOUND_IN_SAFE_MAINTENANCE_SCRIPT"
  exit 1
fi

test -s "$report"

echo "report=$report"
echo "vacuum_analyze_applied=$vacuum_count"
echo "analyze_applied=$analyze_count"
echo "delete_allowed=0"
echo "drop_allowed=0"
echo "truncate_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_POSTGRES_SAFE_MAINTENANCE_APPLY_V1_READY"
echo "VERDICT=TEST_MARKETCORE_POSTGRES_SAFE_MAINTENANCE_APPLY_V1_OK"
