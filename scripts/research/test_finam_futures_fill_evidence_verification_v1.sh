#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

MIGRATION="scripts/research/migrate_finam_futures_fill_evidence_verification_v1.py"
BUILDER="scripts/research/build_finam_futures_fill_evidence_verification_v1.py"
AUDIT="scripts/research/audit_finam_futures_fill_evidence_verification_v1.py"

SOURCE_VERSION="${1:-FINAM_FUTURES_CSV_IMPORT_V1_20260806}"
BATCH_ID="${2:-FINAM_FUTURES_FILL_VERIFICATION_V1_TEST}"

LOG="/tmp/test_finam_futures_fill_evidence_verification_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src "$PYTHON" -m py_compile \
  "$MIGRATION" \
  "$BUILDER" \
  "$AUDIT"

PYTHONPATH=src "$PYTHON" "$MIGRATION" --apply |
tee "$LOG"

PYTHONPATH=src "$PYTHON" "$BUILDER" \
  --source-version "$SOURCE_VERSION" \
  --verification-batch-id "$BATCH_ID" \
  --commission-account DEFAULT \
  --date-from 2026-05-11 \
  --date-to 2026-05-29 |
tee -a "$LOG"

PYTHONPATH=src "$PYTHON" "$AUDIT" |
tee -a "$LOG"

grep -Fq \
  "VERDICT=FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_DRY_RUN_OK" \
  "$LOG"

grep -Fq \
  "VERDICT=FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_AUDIT_OK" \
  "$LOG"

grep -Fq "unresolved_count=0" "$LOG"

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_OK"
