#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RISK_EVENT_AUDIT_RETENTION_POLICY_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/cleanup_risk_event_audit_retention_policy_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RISK_EVENT_AUDIT_RETENTION_POLICY_V1" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_RETENTION_POLICY_CONFIG" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_RETENTION_POLICY_SUMMARY" "$TMP_LOG"
grep -q "RISK_EVENT_AUDIT_RETENTION_POLICY_V1_OK" "$TMP_LOG"

echo "TEST_RISK_EVENT_AUDIT_RETENTION_POLICY_V1_OK"
