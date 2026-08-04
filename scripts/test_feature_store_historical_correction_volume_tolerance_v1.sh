#!/usr/bin/env bash
set -euo pipefail

AUDIT_FILE="src/scripts/build_feature_store_historical_correction_audit_v1.py"
FORENSIC_FILE="src/scripts/inspect_feature_store_historical_corrections_v1.py"
AUDIT_LOG="/tmp/feature_store_historical_correction_volume_tolerance_audit_v1.log"
FORENSIC_LOG="/tmp/feature_store_historical_correction_volume_tolerance_forensic_v1.log"

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_VOLUME_TOLERANCE_V1 ==="

PYTHONPATH=src python -m py_compile \
  "$AUDIT_FILE" \
  "$FORENSIC_FILE"

python3 - <<'PY'
from pathlib import Path

for filename in (
    "src/scripts/build_feature_store_historical_correction_audit_v1.py",
    "src/scripts/inspect_feature_store_historical_corrections_v1.py",
):
    text = Path(filename).read_text(encoding="utf-8")

    required = [
        "VOLUME_TOLERANCE",
        "FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE",
        "abs(",
        "snapshot.volume - source.volume",
        "> %s::numeric",
    ]

    for token in required:
        if token not in text:
            raise SystemExit(
                f"ERROR=required_contract_missing:{filename}:{token}"
            )

    legacy = (
        "snapshot.volume IS DISTINCT FROM source.volume"
    )

    if legacy in text:
        raise SystemExit(
            f"ERROR=exact_volume_comparison_remains:{filename}"
        )

print("source_contract=OK")
PY

FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE=0.00005 \
PYTHONPATH=src \
python "$AUDIT_FILE" \
  --window-bars 20 \
  --dry-run |
  tee "$AUDIT_LOG"

grep -q "changed_pairs=0" "$AUDIT_LOG" || {
    echo "ERROR=false_positive_changed_pairs_remain"
    exit 1
}

grep -q "changed_rows=0" "$AUDIT_LOG" || {
    echo "ERROR=false_positive_changed_rows_remain"
    exit 1
}

grep -q "dirty_rows_updated=0" "$AUDIT_LOG"

FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE=0.00005 \
PYTHONPATH=src \
python "$FORENSIC_FILE" \
  --window-bars 20 \
  --limit 500 |
  tee "$FORENSIC_LOG"

grep -q "difference_pairs=0" "$FORENSIC_LOG" || {
    echo "ERROR=forensic_false_positive_pairs_remain"
    exit 1
}

grep -q "difference_rows=0" "$FORENSIC_LOG" || {
    echo "ERROR=forensic_false_positive_rows_remain"
    exit 1
}

grep -q "volume_changed_rows=0" "$FORENSIC_LOG"
grep -q "writes_performed=0" "$FORENSIC_LOG"

echo "volume_tolerance=0.00005"
echo "log_file=$AUDIT_LOG"
echo "forensic_log_file=$FORENSIC_LOG"
echo "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_VOLUME_TOLERANCE_V1_OK"
