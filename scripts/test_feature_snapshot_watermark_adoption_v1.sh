#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/build_feature_snapshot_history_backfill_v1.py"
LOG="/tmp/feature_snapshot_watermark_adoption_v1.log"

echo "=== TEST_FEATURE_SNAPSHOT_WATERMARK_ADOPTION_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/build_feature_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

required = [
    "FROM analytics.feature_store_watermark_v1",
    "feature_snapshot_last_ts AS last_feature_ts",
    "UPDATE analytics.feature_store_watermark_v1",
    "feature_snapshot_last_ts =",
    "market_snapshot_last_ts",
    "IS DISTINCT FROM EXCLUDED.return1_pct",
    "IS DISTINCT FROM EXCLUDED.return5_pct",
    "IS DISTINCT FROM EXCLUDED.volume_sma20",
]

for item in required:
    if item not in text:
        raise SystemExit(
            f"ERROR=required_contract_missing:{item}"
        )

legacy = """
SELECT
                            symbol,
                            timeframe,
                            max(bar_ts) AS last_feature_ts
                        FROM analytics.feature_snapshot_v1
                        GROUP BY symbol, timeframe
"""

if legacy in text:
    raise SystemExit(
        "ERROR=legacy_feature_watermark_scan_remains"
    )

print("source_contract=OK")
PY

BEFORE="$(
    psql -X -d finam_core -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            coalesce(
                feature_snapshot_last_ts::text,
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
grep -q "overlap_bars=20" "$LOG"
grep -q "context_bars=40" "$LOG"
grep -q "dry_run=1" "$LOG"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY" \
  "$LOG"

AFTER="$(
    psql -X -d finam_core -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            coalesce(
                feature_snapshot_last_ts::text,
                'NULL'
            ),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$BEFORE" == "$AFTER" ]] || {
    echo "ERROR=dry_run_changed_feature_watermark"
    exit 1
}

PLAN="$(
    psql -X -d finam_core -Atqc "
    EXPLAIN
    SELECT ms.bar_ts
    FROM analytics.feature_store_watermark_v1 w
    JOIN marketcore.market_snapshot_v1 ms
      ON ms.symbol = w.symbol
     AND ms.timeframe = w.timeframe
     AND ms.bar_ts > w.feature_snapshot_last_ts
    LIMIT 1;
    "
)"

printf '%s\n' "$PLAN"

grep -Eq \
  "market_snapshot_v1_pkey|ix_market_snapshot_v1_symbol_tf_ts" \
  <<<"$PLAN" || {
    echo "ERROR=market_snapshot_index_not_used"
    exit 1
}

echo \
  "VERDICT=TEST_FEATURE_SNAPSHOT_WATERMARK_ADOPTION_V1_OK"
