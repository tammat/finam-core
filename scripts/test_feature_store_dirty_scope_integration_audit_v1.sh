#!/usr/bin/env bash
set -euo pipefail

SCRIPT="src/scripts/audit_feature_store_dirty_scope_integration_v1.py"
LOG="/tmp/feature_store_dirty_scope_integration_audit_v1.log"

echo "=== TEST_FEATURE_STORE_DIRTY_SCOPE_INTEGRATION_AUDIT_V1 ==="

[[ -f "$SCRIPT" ]] || {
    echo "ERROR=audit_source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$SCRIPT"

PYTHONPATH=src \
python "$SCRIPT" | tee "$LOG"

grep -q \
  "=== MARKET SNAPSHOT ===" \
  "$LOG" || {
    echo "ERROR=market_section_missing"
    exit 1
}

grep -q \
  "=== FEATURE SNAPSHOT ===" \
  "$LOG" || {
    echo "ERROR=feature_section_missing"
    exit 1
}

grep -q \
  "token=processed_rows =" \
  "$LOG" || {
    echo "ERROR=processed_rows_marker_missing"
    exit 1
}

grep -q \
  "token=feature_store_watermark_v1" \
  "$LOG" || {
    echo "ERROR=watermark_marker_missing"
    exit 1
}

grep -q \
  "VERDICT=FEATURE_STORE_DIRTY_SCOPE_INTEGRATION_AUDIT_V1_READY" \
  "$LOG" || {
    echo "ERROR=audit_verdict_missing"
    exit 1
}

echo "log_file=$LOG"
echo \
  "VERDICT=TEST_FEATURE_STORE_DIRTY_SCOPE_INTEGRATION_AUDIT_V1_OK"
