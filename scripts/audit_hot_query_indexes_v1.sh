#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
LOG_DIR="${LOG_DIR:-/opt/finam-core/runtime/audits}"
LOG_FILE="${LOG_DIR}/hot_query_indexes_v1.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

PSQL=(
    psql
    -X
    -U "$DB_USER"
    -d "$DB_NAME"
    -v ON_ERROR_STOP=1
    -P pager=off
)

echo "=== HOT QUERY INDEX AUDIT V1 ==="
echo "timestamp=$(date -Is)"
echo "database=$DB_NAME"
echo "user=$DB_USER"

"${PSQL[@]}" -Atqc "SELECT 1;" | grep -qx "1"

echo
echo "=== TABLE DEFINITIONS ==="

"${PSQL[@]}" -c "
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    c.reltuples::bigint AS estimated_rows
FROM pg_class c
JOIN pg_namespace n
  ON n.oid = c.relnamespace
WHERE (n.nspname, c.relname) IN (
    ('analytics', 'market_microstructure_snapshot_v1'),
    ('marketcore', 'market_snapshot_v1'),
    ('public', 'market_bars'),
    ('analytics', 'feature_snapshot_v1')
)
ORDER BY pg_total_relation_size(c.oid) DESC;
"

echo
echo "=== COLUMN DEFINITIONS ==="

"${PSQL[@]}" -c "
SELECT
    table_schema,
    table_name,
    ordinal_position,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE (table_schema, table_name) IN (
    ('analytics', 'market_microstructure_snapshot_v1'),
    ('marketcore', 'market_snapshot_v1'),
    ('public', 'market_bars'),
    ('analytics', 'feature_snapshot_v1')
)
ORDER BY table_schema, table_name, ordinal_position;
"

echo
echo "=== EXISTING INDEXES ==="

"${PSQL[@]}" -c "
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE (schemaname, tablename) IN (
    ('analytics', 'market_microstructure_snapshot_v1'),
    ('marketcore', 'market_snapshot_v1'),
    ('public', 'market_bars'),
    ('analytics', 'feature_snapshot_v1')
)
ORDER BY schemaname, tablename, indexname;
"

echo
echo "=== INDEX USAGE ==="

"${PSQL[@]}" -c "
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    s.idx_scan,
    s.idx_tup_read,
    s.idx_tup_fetch,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
WHERE (s.schemaname, s.relname) IN (
    ('analytics', 'market_microstructure_snapshot_v1'),
    ('marketcore', 'market_snapshot_v1'),
    ('public', 'market_bars'),
    ('analytics', 'feature_snapshot_v1')
)
ORDER BY s.schemaname, s.relname, s.idx_scan DESC;
"

echo
echo "=== SAMPLE VALUES ==="

"${PSQL[@]}" -c "
SELECT
    symbol,
    min(observed_at) AS first_observed_at,
    max(observed_at) AS last_observed_at,
    count(*) AS rows
FROM analytics.market_microstructure_snapshot_v1
GROUP BY symbol
ORDER BY rows DESC
LIMIT 10;
"

"${PSQL[@]}" -c "
SELECT
    symbol,
    timeframe,
    min(bar_ts) AS first_bar_ts,
    max(bar_ts) AS last_bar_ts,
    count(*) AS rows
FROM marketcore.market_snapshot_v1
GROUP BY symbol, timeframe
ORDER BY rows DESC
LIMIT 20;
"

echo
echo "=== EXPLAIN MICROSTRUCTURE RECENT ==="

MICRO_SYMBOL="$(
    "${PSQL[@]}" -Atqc "
    SELECT symbol
    FROM analytics.market_microstructure_snapshot_v1
    GROUP BY symbol
    ORDER BY count(*) DESC
    LIMIT 1;
    "
)"

echo "microstructure_sample_symbol=$MICRO_SYMBOL"

MICRO_SYMBOL_SQL="$(
    printf "%s" "$MICRO_SYMBOL" |
    sed "s/'/''/g"
)"

"${PSQL[@]}" <<SQL
EXPLAIN (
    COSTS,
    VERBOSE,
    SETTINGS
)
SELECT
    observed_at,
    lag(observed_at) OVER (ORDER BY observed_at) AS previous_at
FROM analytics.market_microstructure_snapshot_v1
WHERE symbol = '${MICRO_SYMBOL_SQL}'
  AND observed_at >= now() - interval '24 hours';
SQL

echo
echo "=== EXPLAIN MARKET SNAPSHOT LATEST ==="

SNAP_ROW="$(
    "${PSQL[@]}" -AtF $'\t' -c "
    SELECT symbol, timeframe
    FROM marketcore.market_snapshot_v1
    GROUP BY symbol, timeframe
    ORDER BY count(*) DESC
    LIMIT 1;
    "
)"

IFS=$'\t' read -r SNAP_SYMBOL SNAP_TIMEFRAME <<< "$SNAP_ROW"

echo "snapshot_sample_symbol=$SNAP_SYMBOL"
echo "snapshot_sample_timeframe=$SNAP_TIMEFRAME"

SNAP_SYMBOL_SQL="$(
    printf "%s" "$SNAP_SYMBOL" |
    sed "s/'/''/g"
)"
SNAP_TIMEFRAME_SQL="$(
    printf "%s" "$SNAP_TIMEFRAME" |
    sed "s/'/''/g"
)"

"${PSQL[@]}" <<SQL
EXPLAIN (
    COSTS,
    VERBOSE,
    SETTINGS
)
SELECT
    bar_ts,
    close,
    volume
FROM marketcore.market_snapshot_v1
WHERE symbol = '${SNAP_SYMBOL_SQL}'
  AND timeframe = '${SNAP_TIMEFRAME_SQL}'
ORDER BY bar_ts DESC
LIMIT 1;
SQL

echo
echo "=== EXPLAIN MARKET BARS MAX ==="

BAR_ROW="$(
    "${PSQL[@]}" -AtF $'\t' -c "
    SELECT symbol, timeframe
    FROM public.market_bars
    GROUP BY symbol, timeframe
    ORDER BY count(*) DESC
    LIMIT 1;
    "
)"

IFS=$'\t' read -r BAR_SYMBOL BAR_TIMEFRAME <<< "$BAR_ROW"

echo "market_bars_sample_symbol=$BAR_SYMBOL"
echo "market_bars_sample_timeframe=$BAR_TIMEFRAME"

BAR_SYMBOL_SQL="$(
    printf "%s" "$BAR_SYMBOL" |
    sed "s/'/''/g"
)"
BAR_TIMEFRAME_SQL="$(
    printf "%s" "$BAR_TIMEFRAME" |
    sed "s/'/''/g"
)"

"${PSQL[@]}" <<SQL
EXPLAIN (
    COSTS,
    VERBOSE,
    SETTINGS
)
SELECT
    max(ts) AS latest,
    count(*) AS bars
FROM public.market_bars
WHERE symbol = '${BAR_SYMBOL_SQL}'
  AND timeframe = '${BAR_TIMEFRAME_SQL}';
SQL

echo
echo "=== SQL OWNERS IN SOURCE ==="

grep -RIn \
    --include='*.py' \
    --include='*.sql' \
    --include='*.sh' \
    -E \
    'market_microstructure_snapshot_v1|market_snapshot_v1|feature_snapshot_v1|SELECT max\(ts\).*market_bars|ORDER BY .*bar_ts.*DESC' \
    src scripts 2>/dev/null |
    head -250 || true

echo
echo "VERDICT=HOT_QUERY_INDEX_AUDIT_COMPLETE"
