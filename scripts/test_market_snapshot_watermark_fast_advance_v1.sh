#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
FILE="src/scripts/build_market_snapshot_history_backfill_v1.py"
LOG="/tmp/market_snapshot_fast_watermark_advance_v1.log"

echo "=== TEST_MARKET_SNAPSHOT_WATERMARK_FAST_ADVANCE_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/build_market_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

required = [
    "WITH latest_state AS",
    "FROM analytics.feature_store_watermark_v1 w",
    "CROSS JOIN LATERAL",
    "ms.symbol = w.symbol",
    "ms.timeframe = w.timeframe",
    "ORDER BY ms.bar_ts DESC",
    "LIMIT 1",
    "FROM latest_state",
    "w.symbol = latest_state.symbol",
    "w.timeframe = latest_state.timeframe",
    "market_snapshot_last_ts =",
]

for item in required:
    if item not in text:
        raise SystemExit(
            f"ERROR=fast_watermark_contract_missing:{item}"
        )

for forbidden in [
    "SELECT DISTINCT ON (\n"
    "                            symbol,\n"
    "                            timeframe",
    "FROM marketcore.market_snapshot_v1\n"
    "                        ORDER BY\n"
    "                            symbol,\n"
    "                            timeframe",
]:
    if forbidden in text:
        raise SystemExit(
            "ERROR=legacy_distinct_on_watermark_query_remains"
        )

print("source_contract=OK")
PY

echo
echo "=== EXPLAIN FAST WATERMARK ADVANCE ==="

PLAN="$(
    psql -X -d "$DB_NAME" -Atqc "
    EXPLAIN
    SELECT
        w.symbol,
        w.timeframe,
        latest_state.last_bar_ts
    FROM analytics.feature_store_watermark_v1 w
    CROSS JOIN LATERAL (
        SELECT ms.bar_ts AS last_bar_ts
        FROM marketcore.market_snapshot_v1 ms
        WHERE ms.symbol = w.symbol
          AND ms.timeframe = w.timeframe
        ORDER BY ms.bar_ts DESC
        LIMIT 1
    ) latest_state;
    "
)"

printf '%s\n' "$PLAN"

grep -Eq \
  'market_snapshot_v1_pkey|ix_market_snapshot_v1_symbol_tf_ts' \
  <<<"$PLAN" || {
    echo "ERROR=market_snapshot_latest_index_not_used"
    exit 1
}

if grep -qE \
  'Unique|Sort.*symbol.*timeframe|Seq Scan on market_snapshot_v1' \
  <<<"$PLAN"
then
    echo "ERROR=legacy_full_snapshot_scan_detected"
    exit 1
fi

BEFORE_HASH="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            coalesce(
                market_snapshot_last_ts::text,
                'NULL'
            ),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$FILE" --dry-run |
    tee "$LOG"

grep -q "mode=incremental" "$LOG"
grep -q "dry_run=1" "$LOG"

grep -q \
  "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
  "$LOG"

AFTER_HASH="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            coalesce(
                market_snapshot_last_ts::text,
                'NULL'
            ),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$BEFORE_HASH" == "$AFTER_HASH" ]] || {
    echo "ERROR=dry_run_changed_watermark"
    exit 1
}

echo "watermark_dry_run_unchanged=1"
echo "VERDICT=TEST_MARKET_SNAPSHOT_WATERMARK_FAST_ADVANCE_V1_OK"
