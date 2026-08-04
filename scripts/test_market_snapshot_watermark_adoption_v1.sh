#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/build_market_snapshot_history_backfill_v1.py"
LOG="/tmp/market_snapshot_watermark_adoption_v1.log"

echo "=== TEST_MARKET_SNAPSHOT_WATERMARK_ADOPTION_V1 ==="

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
    "FROM analytics.feature_store_watermark_v1",
    "market_snapshot_last_ts AS last_bar_ts",
    "UPDATE analytics.feature_store_watermark_v1",
    "market_snapshot_last_ts =",
    "IS DISTINCT FROM EXCLUDED.open",
    "IS DISTINCT FROM EXCLUDED.close",
    "IS DISTINCT FROM EXCLUDED.volume",
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
                            max(bar_ts) AS last_bar_ts
                        FROM marketcore.market_snapshot_v1
                        GROUP BY symbol, timeframe
"""

if legacy in text:
    raise SystemExit(
        "ERROR=legacy_full_watermark_scan_remains"
    )

print("source_contract=OK")
PY

BEFORE="$(
    psql -X -d finam_core -Atqc "
    SELECT count(*) FILTER (
        WHERE updated_at >= now() - interval '60 seconds'
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$FILE" \
    --dry-run |
    tee "$LOG"

grep -q "mode=incremental" "$LOG"
grep -q "overlap_bars=20" "$LOG"
grep -q "dry_run=1" "$LOG"

grep -q \
  "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
  "$LOG"

AFTER="$(
    psql -X -d finam_core -Atqc "
    SELECT count(*) FILTER (
        WHERE updated_at >= now() - interval '60 seconds'
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$BEFORE" == "$AFTER" ]] || {
    echo "ERROR=dry_run_changed_watermark"
    exit 1
}

PLAN="$(
    psql -X -d finam_core -Atqc "
    EXPLAIN
    SELECT
        mb.ts
    FROM analytics.feature_store_watermark_v1 w
    JOIN public.market_bars mb
      ON mb.symbol=w.symbol
     AND mb.timeframe=w.timeframe
     AND mb.ts>w.market_snapshot_last_ts
    LIMIT 1;
    "
)"

printf '%s\n' "$PLAN"

grep -Eq \
  "market_bars_pkey|idx_market_bars_symbol_tf_ts" \
  <<<"$PLAN" || {
    echo "ERROR=market_bars_index_not_used"
    exit 1
}

echo "VERDICT=TEST_MARKET_SNAPSHOT_WATERMARK_ADOPTION_V1_OK"
