#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
SCRIPT="src/scripts/build_feature_store_watermark_v1.py"
LOG="/tmp/feature_store_watermark_v1.log"

echo "=== TEST_FEATURE_STORE_WATERMARK_V1 ==="

[[ -f "$SCRIPT" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$SCRIPT"

DATABASE_URL="postgresql:///$DB_NAME" \
PYTHONPATH=src \
python "$SCRIPT" | tee "$LOG"

grep -q \
  "VERDICT=FEATURE_STORE_WATERMARK_V1_READY" \
  "$LOG" || {
    echo "ERROR=watermark_verdict_missing"
    exit 1
}

psql -X -d "$DB_NAME" -Atqc "
SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='analytics'
      AND table_name='feature_store_watermark_v1'
);
" | grep -qx "t" || {
    echo "ERROR=watermark_table_missing"
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
    ) duplicate_rows;
    "
)"

[[ "$DUPLICATES" == "0" ]] || {
    echo "ERROR=watermark_duplicates:$DUPLICATES"
    exit 1
}

ROWS="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$ROWS" -gt 0 ]] || {
    echo "ERROR=watermark_empty"
    exit 1
}

echo "watermark_rows=$ROWS"
echo "VERDICT=TEST_FEATURE_STORE_WATERMARK_V1_OK"
