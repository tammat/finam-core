#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/build_feature_store_historical_correction_audit_v1.py"
LOG="/tmp/feature_store_historical_correction_audit_v1.log"
DB_NAME="${DB_NAME:-finam_core}"

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/"
    "build_feature_store_historical_correction_audit_v1.py"
).read_text(encoding="utf-8")

required = [
    "FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1",
    "feature_store_historical_correction_audit_v1",
    "feature_store_watermark_v1",
    "CROSS JOIN LATERAL",
    "ORDER BY mb.ts DESC",
    "LIMIT %s",
    "IS DISTINCT FROM source.open",
    "IS DISTINCT FROM source.high",
    "IS DISTINCT FROM source.low",
    "IS DISTINCT FROM source.close",
    "IS DISTINCT FROM source.volume",
    "market_dirty = true",
    "dirty_rows_updated",
    "--dry-run",
]

for token in required:
    if token not in text:
        raise SystemExit(
            f"ERROR=source_contract_missing:{token}"
        )

forbidden = [
    "DELETE FROM marketcore.market_snapshot_v1",
    "DELETE FROM analytics.feature_snapshot_v1",
    "UPDATE marketcore.market_snapshot_v1",
    "UPDATE analytics.feature_snapshot_v1",
]

for token in forbidden:
    if token in text:
        raise SystemExit(
            f"ERROR=forbidden_write_present:{token}"
        )

print("source_contract=OK")
PY

BEFORE="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            market_dirty::text || '|' ||
            coalesce(
                market_dirty_at::text,
                'NULL'
            ),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

FEATURE_STORE_CORRECTION_WINDOW_BARS=20 \
PYTHONPATH=src \
python "$FILE" \
  --window-bars 20 \
  --dry-run |
    tee "$LOG"

grep -q \
  "=== FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1 ===" \
  "$LOG"

grep -q "window_bars=20" "$LOG"
grep -q "dry_run=1" "$LOG"
grep -q "runtime_changed=0" "$LOG"
grep -q "execution_changed=0" "$LOG"
grep -q "orders_changed=0" "$LOG"
grep -q "fills_changed=0" "$LOG"
grep -q "micro_live_allowed=0" "$LOG"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY" \
  "$LOG"

AFTER="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            market_dirty::text || '|' ||
            coalesce(
                market_dirty_at::text,
                'NULL'
            ),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$BEFORE" == "$AFTER" ]] || {
    echo "ERROR=dry_run_changed_watermark"
    exit 1
}

PLAN="$(
    psql -X -d "$DB_NAME" -Atqc "
    EXPLAIN
    SELECT source_bar.ts
    FROM analytics.feature_store_watermark_v1 w
    CROSS JOIN LATERAL (
        SELECT mb.ts
        FROM public.market_bars mb
        WHERE mb.symbol = w.symbol
          AND mb.timeframe = w.timeframe
          AND mb.ts IS NOT NULL
          AND mb.close IS NOT NULL
        ORDER BY mb.ts DESC
        LIMIT 20
    ) source_bar;
    "
)"

printf '%s\n' "$PLAN"

grep -Eq \
  "market_bars_pkey|idx_market_bars_symbol_tf_ts" \
  <<<"$PLAN" || {
    echo "ERROR=market_bars_index_not_used"
    exit 1
}

if grep -q \
  "Seq Scan on market_bars" \
  <<<"$PLAN"; then
    echo "ERROR=market_bars_sequential_scan_present"
    exit 1
fi

echo "log_file=$LOG"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_OK"
