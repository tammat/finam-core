#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
MAX_IDLE_READ_BLOCKS="${MAX_IDLE_READ_BLOCKS:-200000}"

echo "=== TEST_FEATURE_STORE_IDLE_READ_AMPLIFICATION_V1 ==="

read -r MARKET_CALLS MARKET_ROWS MARKET_READS FEATURE_CALLS FEATURE_ROWS FEATURE_READS < <(
    psql -X -d "$DB_NAME" -AtF ' ' -c "
    WITH statements AS (
        SELECT
            CASE
                WHEN query ILIKE '%INSERT INTO marketcore.market_snapshot_v1%'
                    THEN 'MARKET'
                WHEN query ILIKE '%INSERT INTO analytics.feature_snapshot_v1%'
                    THEN 'FEATURE'
            END AS component,
            calls,
            rows,
            shared_blks_read
        FROM pg_stat_statements
        WHERE query ILIKE '%feature_store_watermark_v1%'
          AND (
              query ILIKE '%INSERT INTO marketcore.market_snapshot_v1%'
              OR query ILIKE '%INSERT INTO analytics.feature_snapshot_v1%'
          )
    )
    SELECT
        coalesce(max(calls) FILTER (WHERE component='MARKET'), 0),
        coalesce(max(rows) FILTER (WHERE component='MARKET'), 0),
        coalesce(max(shared_blks_read) FILTER (WHERE component='MARKET'), 0),
        coalesce(max(calls) FILTER (WHERE component='FEATURE'), 0),
        coalesce(max(rows) FILTER (WHERE component='FEATURE'), 0),
        coalesce(max(shared_blks_read) FILTER (WHERE component='FEATURE'), 0)
    FROM statements;
    "
)

echo "market_calls=$MARKET_CALLS"
echo "market_rows=$MARKET_ROWS"
echo "market_read_blocks=$MARKET_READS"
echo "feature_calls=$FEATURE_CALLS"
echo "feature_rows=$FEATURE_ROWS"
echo "feature_read_blocks=$FEATURE_READS"

TOTAL_READS=$((MARKET_READS + FEATURE_READS))

if (( MARKET_ROWS == 0 && FEATURE_ROWS == 0 && TOTAL_READS > MAX_IDLE_READ_BLOCKS )); then
    echo "status=IDLE_READ_AMPLIFICATION_CONFIRMED"
else
    echo "status=IDLE_READ_AMPLIFICATION_NOT_CONFIRMED"
fi

echo "total_read_blocks=$TOTAL_READS"
echo "VERDICT=TEST_FEATURE_STORE_IDLE_READ_AMPLIFICATION_V1_OK"
