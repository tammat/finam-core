#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
LOG="runtime/audits/feature_store_incremental_performance_v1.log"

echo "=== TEST_FEATURE_STORE_INCREMENTAL_PERFORMANCE_V1 ==="

mkdir -p runtime/audits

psql -X -d "$DB_NAME" -P pager=off -AtF $'\t' -c "
SELECT
    queryid,
    calls,
    round(mean_exec_time::numeric, 2),
    shared_blks_read,
    temp_blks_written,
    regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g')
FROM pg_stat_statements
WHERE query ILIKE '%feature_snapshot_v1%'
   OR query ILIKE '%market_snapshot_v1%'
ORDER BY total_exec_time DESC;
" | tee "$LOG"

[[ -s "$LOG" ]] || {
    echo "ERROR=performance_log_missing"
    exit 1
}

grep -q \
    "WITH watermark AS" \
    "$LOG" || {
        echo "ERROR=incremental_market_query_missing"
        exit 1
    }

grep -q \
    "historical_context" \
    "$LOG" || {
        echo "ERROR=incremental_feature_query_missing"
        exit 1
    }

if grep -q \
    "ORDER BY ts DESC LIMIT 200000" \
    "$LOG"
then
    echo "ERROR=legacy_full_market_refresh_executed"
    exit 1
fi

if grep -qE \
    $'\t[1-9][0-9]*\t.*\t.*\t[1-9][0-9]*\t.*historical_context' \
    "$LOG"
then
    echo "ERROR=incremental_feature_temp_writes_detected"
    exit 1
fi

echo "log_file=$LOG"
echo "VERDICT=TEST_FEATURE_STORE_INCREMENTAL_PERFORMANCE_V1_OK"
