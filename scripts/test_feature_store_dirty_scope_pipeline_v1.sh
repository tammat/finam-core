#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"

MARKET_FILE="src/scripts/build_market_snapshot_history_backfill_v1.py"
FEATURE_FILE="src/scripts/build_feature_snapshot_history_backfill_v1.py"

MARKET_LOG="/tmp/feature_store_dirty_market_v1.log"
FEATURE_LOG="/tmp/feature_store_dirty_feature_v1.log"

echo "=== TEST_FEATURE_STORE_DIRTY_SCOPE_PIPELINE_V1 ==="

for file in "$MARKET_FILE" "$FEATURE_FILE"
do
    [[ -f "$file" ]] || {
        echo "ERROR=source_missing:$file"
        exit 1
    }

    PYTHONPATH=src python -m py_compile "$file"
done

python3 - <<'PY'
from pathlib import Path

market = Path(
    "src/scripts/build_market_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

feature = Path(
    "src/scripts/build_feature_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

market_required = [
    "RETURNING symbol, timeframe",
    "changed_pairs",
    "psycopg2.extras.execute_values",
    "market_dirty = true",
    "market_dirty_at = clock_timestamp()",
]

feature_required = [
    "WHERE market_dirty",
    "market_dirty = false",
    "feature_processed_at = clock_timestamp()",
    "feature_snapshot_last_ts =",
    "market_snapshot_last_ts",
]

for token in market_required:
    if token not in market:
        raise SystemExit(
            f"ERROR=market_contract_missing:{token}"
        )

for token in feature_required:
    if token not in feature:
        raise SystemExit(
            f"ERROR=feature_contract_missing:{token}"
        )

print("source_contract=OK")
PY

BEFORE_DIRTY="$(
    psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE market_dirty;
    "
)"

echo "dirty_before=$BEFORE_DIRTY"

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$MARKET_FILE" |
    tee "$MARKET_LOG"

grep -q "mode=incremental" "$MARKET_LOG"
grep -q \
  "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
  "$MARKET_LOG"

DIRTY_AFTER_MARKET="$(
    psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE market_dirty;
    "
)"

echo "dirty_after_market=$DIRTY_AFTER_MARKET"

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$FEATURE_FILE" |
    tee "$FEATURE_LOG"

grep -q "mode=incremental" "$FEATURE_LOG"
grep -q \
  "VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY" \
  "$FEATURE_LOG"

DIRTY_AFTER_FEATURE="$(
    psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE market_dirty;
    "
)"

WATERMARK_LAG="$(
    psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE feature_snapshot_last_ts
          IS DISTINCT FROM market_snapshot_last_ts;
    "
)"

echo "dirty_after_feature=$DIRTY_AFTER_FEATURE"
echo "watermark_lag=$WATERMARK_LAG"

[[ "$DIRTY_AFTER_FEATURE" == "0" ]] || {
    echo "ERROR=dirty_rows_not_consumed:$DIRTY_AFTER_FEATURE"
    exit 1
}

[[ "$WATERMARK_LAG" == "0" ]] || {
    echo "ERROR=watermark_lag:$WATERMARK_LAG"
    exit 1
}

echo "VERDICT=TEST_FEATURE_STORE_DIRTY_SCOPE_PIPELINE_V1_OK"
