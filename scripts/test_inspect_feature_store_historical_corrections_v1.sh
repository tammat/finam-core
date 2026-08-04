#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/inspect_feature_store_historical_corrections_v1.py"
LOG="/tmp/feature_store_historical_correction_forensic_v1.log"
DB_NAME="${DB_NAME:-finam_core}"

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/inspect_feature_store_historical_corrections_v1.py"
).read_text(encoding="utf-8")

required = [
    "conn.set_session(readonly=True",
    "CROSS JOIN LATERAL",
    "ORDER BY mb.ts DESC",
    "IS DISTINCT FROM snapshot.open",
    "IS DISTINCT FROM snapshot.high",
    "IS DISTINCT FROM snapshot.low",
    "IS DISTINCT FROM snapshot.close",
    "IS DISTINCT FROM snapshot.volume",
    "writes_performed=0",
]

for token in required:
    if token not in text:
        raise SystemExit(
            f"ERROR=required_contract_missing:{token}"
        )

forbidden = [
    "INSERT INTO",
    "UPDATE analytics.feature_store_watermark_v1",
    "DELETE FROM",
]

for token in forbidden:
    if token in text:
        raise SystemExit(
            f"ERROR=write_contract_present:{token}"
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
            coalesce(market_dirty_at::text, 'NULL'),
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
  --limit 500 |
    tee "$LOG"

AFTER="$(
    psql -X -d "$DB_NAME" -Atqc "
    SELECT md5(
        string_agg(
            symbol || '|' ||
            timeframe || '|' ||
            market_dirty::text || '|' ||
            coalesce(market_dirty_at::text, 'NULL'),
            ',' ORDER BY symbol, timeframe
        )
    )
    FROM analytics.feature_store_watermark_v1;
    "
)"

[[ "$BEFORE" == "$AFTER" ]] || {
    echo "ERROR=forensic_changed_watermark"
    exit 1
}

grep -q "difference_pairs=3" "$LOG" || {
    echo "ERROR=unexpected_difference_pair_count"
    exit 1
}

grep -q "difference_rows=54" "$LOG" || {
    echo "ERROR=unexpected_difference_row_count"
    exit 1
}

grep -q "writes_performed=0" "$LOG"

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1_READY" \
  "$LOG"

echo "log_file=$LOG"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_FORENSIC_V1_OK"
