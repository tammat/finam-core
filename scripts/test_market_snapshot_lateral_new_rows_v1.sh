#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-alex}"
FILE="src/scripts/build_market_snapshot_history_backfill_v1.py"
LOG="runtime/audits/market_snapshot_lateral_new_rows_v1.log"

echo "=== TEST_MARKET_SNAPSHOT_LATERAL_NEW_ROWS_V1 ==="

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
    "new_rows AS",
    "FROM watermark w",
    "CROSS JOIN LATERAL",
    "mb.ts > w.last_bar_ts",
    "ORDER BY mb.ts",
    "changed_scope AS",
    "RETURNING symbol, timeframe",
]

for token in required:
    if token not in text:
        raise SystemExit(
            f"ERROR=source_contract_missing:{token}"
        )

legacy = """JOIN public.market_bars mb
                          ON mb.symbol = w.symbol"""

if legacy in text:
    raise SystemExit(
        "ERROR=legacy_bulk_market_bars_join_remains"
    )

print("source_contract=OK")
PY

mkdir -p "$(dirname "$LOG")"

PLAN="$(
    psql -X -U "$DB_USER" -d "$DB_NAME" -Atqc "
    EXPLAIN
    WITH watermark AS (
        SELECT
            symbol,
            timeframe,
            market_snapshot_last_ts AS last_bar_ts
        FROM analytics.feature_store_watermark_v1
        WHERE market_snapshot_last_ts IS NOT NULL
    )
    SELECT new_bar.ts
    FROM watermark w
    CROSS JOIN LATERAL (
        SELECT mb.ts
        FROM public.market_bars mb
        WHERE mb.symbol = w.symbol
          AND mb.timeframe = w.timeframe
          AND mb.ts > w.last_bar_ts
          AND mb.close IS NOT NULL
        ORDER BY mb.ts
    ) new_bar;
    "
)"

printf '%s\n' "$PLAN" | tee "$LOG"

grep -Eq \
  "market_bars_pkey|idx_market_bars_symbol_tf_ts" \
  <<<"$PLAN" || {
    echo "ERROR=market_bars_parameterized_index_not_used"
    exit 1
}

if grep -q "Seq Scan on market_bars" <<<"$PLAN"; then
    echo "ERROR=market_bars_sequential_scan_present"
    exit 1
fi

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$FILE" --dry-run |
    tee -a "$LOG"

grep -q "mode=incremental" "$LOG"
grep -q "dry_run=1" "$LOG"
grep -q \
  "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
  "$LOG"

echo "log_file=$LOG"
echo "VERDICT=TEST_MARKET_SNAPSHOT_LATERAL_NEW_ROWS_V1_OK"
