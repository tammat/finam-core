#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_session_side_gate_runtime_audit_summary_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1" "$TMP_LOG"
grep -q "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_STATUS" "$TMP_LOG"
grep -q "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1_OK" "$TMP_LOG"

echo "TEST_SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1_OK"
