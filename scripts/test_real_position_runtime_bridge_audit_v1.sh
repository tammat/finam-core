#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_real_position_runtime_bridge_audit_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1" "$TMP_LOG"
grep -q "REAL_POSITION_RUNTIME_BRIDGE_SUMMARY" "$TMP_LOG"
grep -q "REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1_OK" "$TMP_LOG"

echo "TEST_REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1_OK"
