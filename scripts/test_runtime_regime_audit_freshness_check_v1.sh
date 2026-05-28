#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_regime_audit_freshness_check_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1" "$TMP_LOG"
grep -q "RUNTIME_REGIME_AUDIT_FRESHNESS_STATUS" "$TMP_LOG"
grep -q "RUNTIME_REGIME_AUDIT_FRESHNESS_ROW" "$TMP_LOG"
grep -q "RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_REGIME_AUDIT_FRESHNESS_CHECK_V1_OK"
