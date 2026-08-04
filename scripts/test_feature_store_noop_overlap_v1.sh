#!/usr/bin/env bash
set -euo pipefail

MARKET_SCRIPT="src/scripts/build_market_snapshot_history_backfill_v1.py"
FEATURE_SCRIPT="src/scripts/build_feature_snapshot_history_backfill_v1.py"

MARKET_LOG_1="/tmp/market_noop_overlap_cycle_1.log"
MARKET_LOG_2="/tmp/market_noop_overlap_cycle_2.log"
FEATURE_LOG_1="/tmp/feature_noop_overlap_cycle_1.log"
FEATURE_LOG_2="/tmp/feature_noop_overlap_cycle_2.log"

echo "=== TEST_FEATURE_STORE_NOOP_OVERLAP_V1 ==="

PYTHONPATH=src python -m py_compile \
    "$MARKET_SCRIPT" \
    "$FEATURE_SCRIPT"

python3 - <<'PY'
from pathlib import Path

market = Path(
    "src/scripts/build_market_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

feature = Path(
    "src/scripts/build_feature_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

required_market = [
    "market_snapshot_v1.open",
    "market_snapshot_v1.close",
    "market_snapshot_v1.volume",
    "IS DISTINCT FROM EXCLUDED.open",
]

required_feature = [
    "feature_snapshot_v1.return1_pct",
    "feature_snapshot_v1.return5_pct",
    "feature_snapshot_v1.volume_sma20",
    "feature_snapshot_v1.volume_ratio20",
]

for item in required_market:
    if item not in market:
        raise SystemExit(
            f"ERROR=market_guard_missing:{item}"
        )

for item in required_feature:
    if item not in feature:
        raise SystemExit(
            f"ERROR=feature_guard_missing:{item}"
        )

for forbidden in [
    "market_snapshot_v1.freshness_sec\n"
    "                            IS DISTINCT FROM",
    "market_snapshot_v1.quality_status\n"
    "                            IS DISTINCT FROM",
]:
    if forbidden in market:
        raise SystemExit(
            f"ERROR=market_time_guard_remains:{forbidden}"
        )

for forbidden in [
    "feature_snapshot_v1.freshness_sec\n"
    "                        IS DISTINCT FROM",
    "feature_snapshot_v1.market_quality_status\n"
    "                        IS DISTINCT FROM",
    "feature_snapshot_v1.feature_quality_score\n"
    "                        IS DISTINCT FROM",
]:
    if forbidden in feature:
        raise SystemExit(
            f"ERROR=feature_time_guard_remains:{forbidden}"
        )

print("source_contract=OK")
PY

run_cycle() {
    local market_log="$1"
    local feature_log="$2"

    FEATURE_STORE_MODE=incremental \
    FEATURE_STORE_OVERLAP_BARS=20 \
    PYTHONPATH=src \
    python "$MARKET_SCRIPT" |
        tee "$market_log"

    FEATURE_STORE_MODE=incremental \
    FEATURE_STORE_OVERLAP_BARS=20 \
    PYTHONPATH=src \
    python "$FEATURE_SCRIPT" |
        tee "$feature_log"
}

echo
echo "=== CYCLE 1 ==="
run_cycle "$MARKET_LOG_1" "$FEATURE_LOG_1"

echo
echo "=== CYCLE 2 ==="
run_cycle "$MARKET_LOG_2" "$FEATURE_LOG_2"

extract_rows() {
    grep '^processed_rows=' "$1" |
        tail -1 |
        cut -d= -f2
}

MARKET_ROWS_1="$(extract_rows "$MARKET_LOG_1")"
MARKET_ROWS_2="$(extract_rows "$MARKET_LOG_2")"
FEATURE_ROWS_1="$(extract_rows "$FEATURE_LOG_1")"
FEATURE_ROWS_2="$(extract_rows "$FEATURE_LOG_2")"

for value in \
    "$MARKET_ROWS_1" \
    "$MARKET_ROWS_2" \
    "$FEATURE_ROWS_1" \
    "$FEATURE_ROWS_2"
do
    [[ "$value" =~ ^[0-9]+$ ]] || {
        echo "ERROR=invalid_processed_rows:$value"
        exit 1
    }
done

echo "market_cycle_1_rows=$MARKET_ROWS_1"
echo "market_cycle_2_rows=$MARKET_ROWS_2"
echo "feature_cycle_1_rows=$FEATURE_ROWS_1"
echo "feature_cycle_2_rows=$FEATURE_ROWS_2"

MAX_NOOP_ROWS="${MAX_NOOP_ROWS:-50}"

if (( MARKET_ROWS_2 > MAX_NOOP_ROWS )); then
    echo "ERROR=market_noop_churn:$MARKET_ROWS_2"
    exit 1
fi

if (( FEATURE_ROWS_2 > MAX_NOOP_ROWS )); then
    echo "ERROR=feature_noop_churn:$FEATURE_ROWS_2"
    exit 1
fi

WATERMARK_LAG="$(
    psql -X -d finam_core -Atqc "
    SELECT count(*)
    FROM analytics.feature_store_watermark_v1
    WHERE feature_snapshot_last_ts
          IS DISTINCT FROM market_snapshot_last_ts;
    "
)"

[[ "$WATERMARK_LAG" == "0" ]] || {
    echo "ERROR=watermark_lag:$WATERMARK_LAG"
    exit 1
}

echo "watermark_lag=0"
echo "VERDICT=TEST_FEATURE_STORE_NOOP_OVERLAP_V1_OK"
