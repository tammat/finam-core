#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/cleanup_risk_event_audit_test_rows_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_RESULT" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1_OK" "$TMP_LOG"

python src/scripts/analytics/build_risk_event_audit_summary_v1.py

echo "TEST_RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1_OK"
