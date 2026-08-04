#!/usr/bin/env bash
set -uo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
LOG_DIR="${LOG_DIR:-/opt/finam-core/runtime/audits}"
LOG_FILE="${LOG_DIR}/marketcore_postgres_audit_v1.log"

mkdir -p "$LOG_DIR"

exec > >(tee "$LOG_FILE") 2>&1

echo "=== MARKETCORE POSTGRES AUDIT V1 ==="
echo "timestamp=$(date -Is)"
echo "database=$DB_NAME"
echo "user=$DB_USER"

if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR=psql_not_found"
    echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_FAILED"
    exit 1
fi

if ! psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "SELECT 1;" |
    grep -qx "1"; then
    echo "ERROR=postgres_connection_failed"
    echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_FAILED"
    exit 1
fi

echo
echo "=== SERVER SETTINGS ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    name,
    setting,
    unit,
    source
FROM pg_settings
WHERE name IN (
    'max_connections',
    'shared_buffers',
    'effective_cache_size',
    'work_mem',
    'maintenance_work_mem',
    'max_worker_processes',
    'max_parallel_workers',
    'max_parallel_workers_per_gather',
    'effective_io_concurrency',
    'random_page_cost',
    'checkpoint_timeout',
    'max_wal_size',
    'min_wal_size',
    'autovacuum_max_workers'
)
ORDER BY name;
"

echo
echo "=== CONNECTION SUMMARY ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    COALESCE(usename, '-') AS usename,
    COALESCE(NULLIF(application_name, ''), '-') AS application_name,
    COALESCE(state, '-') AS state,
    count(*) AS connections,
    max(now() - query_start) AS longest_query
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
GROUP BY usename, application_name, state
ORDER BY connections DESC, longest_query DESC NULLS LAST;
"

echo
echo "=== ACTIVE QUERIES ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    pid,
    leader_pid,
    usename,
    COALESCE(NULLIF(application_name, ''), '-') AS application_name,
    now() - query_start AS duration,
    wait_event_type,
    wait_event,
    left(
        regexp_replace(query, E'[\\n\\r\\t]+', ' ', 'g'),
        240
    ) AS query
FROM pg_stat_activity
WHERE state <> 'idle'
  AND pid <> pg_backend_pid()
ORDER BY query_start
LIMIT 50;
"

echo
echo "=== LOCK WAITS ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    blocked.pid AS blocked_pid,
    now() - blocked.query_start AS blocked_duration,
    blocker.pid AS blocker_pid,
    now() - blocker.query_start AS blocker_duration,
    left(
        regexp_replace(blocked.query, E'[\\n\\r\\t]+', ' ', 'g'),
        160
    ) AS blocked_query,
    left(
        regexp_replace(blocker.query, E'[\\n\\r\\t]+', ' ', 'g'),
        160
    ) AS blocker_query
FROM pg_stat_activity blocked
JOIN pg_locks blocked_lock
  ON blocked_lock.pid = blocked.pid
 AND NOT blocked_lock.granted
JOIN pg_locks blocker_lock
  ON blocker_lock.locktype = blocked_lock.locktype
 AND blocker_lock.database IS NOT DISTINCT FROM blocked_lock.database
 AND blocker_lock.relation IS NOT DISTINCT FROM blocked_lock.relation
 AND blocker_lock.page IS NOT DISTINCT FROM blocked_lock.page
 AND blocker_lock.tuple IS NOT DISTINCT FROM blocked_lock.tuple
 AND blocker_lock.virtualxid IS NOT DISTINCT FROM blocked_lock.virtualxid
 AND blocker_lock.transactionid IS NOT DISTINCT FROM blocked_lock.transactionid
 AND blocker_lock.classid IS NOT DISTINCT FROM blocked_lock.classid
 AND blocker_lock.objid IS NOT DISTINCT FROM blocked_lock.objid
 AND blocker_lock.objsubid IS NOT DISTINCT FROM blocked_lock.objsubid
 AND blocker_lock.pid <> blocked_lock.pid
 AND blocker_lock.granted
JOIN pg_stat_activity blocker
  ON blocker.pid = blocker_lock.pid
ORDER BY blocked.query_start;
"

echo
echo "=== DATABASE SIZE ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    current_database() AS database,
    pg_size_pretty(pg_database_size(current_database())) AS database_size;
"

echo
echo "=== LARGEST TABLES ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    schemaname,
    relname,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(
        pg_total_relation_size(relid) - pg_relation_size(relid)
    ) AS indexes_and_toast,
    n_live_tup,
    n_dead_tup,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 40;
"

echo
echo "=== CACHE HIT ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    datname,
    blks_read,
    blks_hit,
    round(
        100.0 * blks_hit /
        NULLIF(blks_hit + blks_read, 0),
        2
    ) AS cache_hit_pct,
    temp_files,
    pg_size_pretty(temp_bytes) AS temp_bytes,
    deadlocks
FROM pg_stat_database
WHERE datname = current_database();
"

echo
echo "=== TABLE IO ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    schemaname,
    relname,
    heap_blks_read,
    heap_blks_hit,
    idx_blks_read,
    idx_blks_hit,
    round(
        100.0 * heap_blks_hit /
        NULLIF(heap_blks_hit + heap_blks_read, 0),
        2
    ) AS heap_cache_hit_pct
FROM pg_statio_user_tables
ORDER BY heap_blks_read DESC
LIMIT 30;
"

echo
echo "=== SEQUENTIAL SCANS ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    n_live_tup,
    CASE
        WHEN seq_scan = 0 THEN 0
        ELSE seq_tup_read / seq_scan
    END AS avg_rows_per_seq_scan
FROM pg_stat_user_tables
ORDER BY seq_tup_read DESC
LIMIT 30;
"

echo
echo "=== DEAD TUPLES ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    round(
        100.0 * n_dead_tup /
        NULLIF(n_live_tup + n_dead_tup, 0),
        2
    ) AS dead_tuple_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY dead_tuple_pct DESC NULLS LAST, n_dead_tup DESC
LIMIT 30;
"

echo
echo "=== LONG TRANSACTIONS ==="

psql -X -U "$DB_USER" -d "$DB_NAME" -P pager=off -c "
SELECT
    pid,
    usename,
    COALESCE(NULLIF(application_name, ''), '-') AS application_name,
    state,
    now() - xact_start AS transaction_age,
    now() - query_start AS query_age,
    wait_event_type,
    wait_event,
    left(
        regexp_replace(query, E'[\\n\\r\\t]+', ' ', 'g'),
        200
    ) AS query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND pid <> pg_backend_pid()
ORDER BY xact_start
LIMIT 30;
"

echo
echo "=== SYSTEM LOAD SNAPSHOT ==="

uptime
free -h

ps -eo pid,ppid,%cpu,%mem,rss,etime,stat,cmd \
    --sort=-%cpu |
    grep -E 'postgres|finam-core|MarketCore|python' |
    grep -v grep |
    head -40 || true

echo
echo "VERDICT=MARKETCORE_POSTGRES_AUDIT_COMPLETE"
