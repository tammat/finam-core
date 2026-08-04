#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
SCRIPT="src/scripts/build_feature_store_dirty_scope_v1.py"
LOG="/tmp/feature_store_dirty_scope_v1.log"

echo "=== TEST_FEATURE_STORE_DIRTY_SCOPE_V1 ==="

[[ -f "$SCRIPT" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$SCRIPT"

DATABASE_URL="postgresql:///$DB_NAME" \
PYTHONPATH=src \
python "$SCRIPT" | tee "$LOG"

grep -q \
  "VERDICT=FEATURE_STORE_DIRTY_SCOPE_V1_READY" \
  "$LOG" || {
    echo "ERROR=dirty_scope_verdict_missing"
    exit 1
}

for column in \
    market_dirty \
    market_dirty_at \
    feature_processed_at
do
    EXISTS="$(
        psql -X -d "$DB_NAME" -Atqc "
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='analytics'
              AND table_name='feature_store_watermark_v1'
              AND column_name='${column}'
        );
        "
    )"

    [[ "$EXISTS" == "t" ]] || {
        echo "ERROR=column_missing:$column"
        exit 1
    }
done

BAD_NULLS="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE market_dirty IS NULL;
    "
)"

[[ "$BAD_NULLS" == "0" ]] || {
    echo "ERROR=market_dirty_nulls:$BAD_NULLS"
    exit 1
}

DUPLICATES="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM (
        SELECT symbol, timeframe
        FROM analytics.feature_store_watermark_v1
        GROUP BY symbol, timeframe
        HAVING count(*) > 1
    ) d;
    "
)"

[[ "$DUPLICATES" == "0" ]] || {
    echo "ERROR=watermark_duplicates:$DUPLICATES"
    exit 1
}

echo "VERDICT=TEST_FEATURE_STORE_DIRTY_SCOPE_V1_OK"
