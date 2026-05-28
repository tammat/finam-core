#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_BROKER_POSITION_RECONCILIATION_AUDIT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_broker_position_reconciliation_audit_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "BROKER_POSITION_RECONCILIATION_AUDIT_V1" "$TMP_LOG"
grep -q "BROKER_POSITION_RECONCILIATION_AUDIT_V1_OK" "$TMP_LOG"

echo "TEST_BROKER_POSITION_RECONCILIATION_AUDIT_V1_OK"
