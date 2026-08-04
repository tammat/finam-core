#!/usr/bin/env bash
set -uo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
LOG_DIR="${LOG_DIR:-/opt/finam-core/runtime/audits}"
LOG_FILE="${LOG_DIR}/pg_stat_statements_audit_v1.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

echo "=== PG_STAT_STATEMENTS AUDIT V1 ==="
echo "timestamp=$(date -Is)"
echo "database=$DB_NAME"
echo "user=$DB_USER"

PSQL=(
    psql
    -X
    -U "$DB_USER"
    -d "$DB_NAME"
    -v ON_ERROR_STOP=1
    -P pager=off
)

if ! "${PSQL[@]}" -Atqc "SELECT 1;" | grep -qx "1"; then
    echo "ERROR=postgres_connection_failed"
    echo "VERDICT=PG_STAT_STATEMENTS_AUDIT_FAILED"
    exit 1
fi

echo
echo "=== EXTENSION STATUS ==="

"${PSQL[@]}" -c "
SELECT
    name,
    default_version,
    installed_version
FROM pg_available_extensions
WHERE name = 'pg_stat_statements';
"

INSTALLED="$(
    "${PSQL[@]}" -Atqc "
    SELECT EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'pg_stat_statements'
    );
    "
)"

PRELOADED="$(
    "${PSQL[@]}" -Atqc "
    SELECT position(
        'pg_stat_statements'
        IN current_setting('shared_preload_libraries')
    ) > 0;
    "
)"

echo "extension_installed=$INSTALLED"
echo "extension_preloaded=$PRELOADED"

if [[ "$INSTALLED" != "t" ]]; then
    echo
    echo "STATUS=PG_STAT_STATEMENTS_NOT_INSTALLED"
    echo "VERDICT=PG_STAT_STATEMENTS_AUDIT_PREREQUISITE_MISSING"
    exit 2
fi

echo
echo "=== TOP BY TOTAL EXECUTION TIME ==="

"${PSQL[@]}" -c "
SELECT
    queryid,
    calls,
    round(total_exec_time::numeric, 2) AS total_exec_ms,
    round(mean_exec_time::numeric, 2) AS mean_exec_ms,
    rows,
    shared_blks_read,
    shared_blks_hit,
    temp_blks_read,
    temp_blks_written,
    left(
        regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g'),
        260
    ) AS query
FROM pg_stat_statements
WHERE dbid = (
    SELECT oid
    FROM pg_database
    WHERE datname = current_database()
)
ORDER BY total_exec_time DESC
LIMIT 30;
"

echo
echo "=== TOP BY TEMP WRITES ==="

"${PSQL[@]}" -c "
SELECT
    queryid,
    calls,
    temp_blks_written,
    pg_size_pretty(
        temp_blks_written::bigint *
        current_setting('block_size')::bigint
    ) AS temp_written,
    round(mean_exec_time::numeric, 2) AS mean_exec_ms,
    left(
        regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g'),
        260
    ) AS query
FROM pg_stat_statements
WHERE temp_blks_written > 0
  AND dbid = (
      SELECT oid
      FROM pg_database
      WHERE datname = current_database()
  )
ORDER BY temp_blks_written DESC
LIMIT 30;
"

echo
echo "=== TOP BY PHYSICAL READS ==="

"${PSQL[@]}" -c "
SELECT
    queryid,
    calls,
    shared_blks_read,
    pg_size_pretty(
        shared_blks_read::bigint *
        current_setting('block_size')::bigint
    ) AS physical_read,
    shared_blks_hit,
    round(mean_exec_time::numeric, 2) AS mean_exec_ms,
    left(
        regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g'),
        260
    ) AS query
FROM pg_stat_statements
WHERE shared_blks_read > 0
  AND dbid = (
      SELECT oid
      FROM pg_database
      WHERE datname = current_database()
  )
ORDER BY shared_blks_read DESC
LIMIT 30;
"

echo
echo "=== TOP BY CALL COUNT ==="

"${PSQL[@]}" -c "
SELECT
    queryid,
    calls,
    rows,
    round(total_exec_time::numeric, 2) AS total_exec_ms,
    round(mean_exec_time::numeric, 4) AS mean_exec_ms,
    left(
        regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g'),
        260
    ) AS query
FROM pg_stat_statements
WHERE dbid = (
    SELECT oid
    FROM pg_database
    WHERE datname = current_database()
)
ORDER BY calls DESC
LIMIT 30;
"

echo
echo "=== STATEMENT SUMMARY ==="

"${PSQL[@]}" -c "
SELECT
    count(*) AS statements,
    sum(calls) AS total_calls,
    pg_size_pretty(
        sum(shared_blks_read)::bigint *
        current_setting('block_size')::bigint
    ) AS physical_reads,
    pg_size_pretty(
        sum(temp_blks_written)::bigint *
        current_setting('block_size')::bigint
    ) AS temp_writes
FROM pg_stat_statements
WHERE dbid = (
    SELECT oid
    FROM pg_database
    WHERE datname = current_database()
);
"

echo
echo "VERDICT=PG_STAT_STATEMENTS_AUDIT_COMPLETE"
exit 0
