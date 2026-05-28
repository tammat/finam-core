#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_RISK_REGIME_STATS_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_risk_regime_stats_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_RISK_REGIME_STATS_V1" "$TMP_LOG"
grep -q "RUNTIME_RISK_REGIME_STATUS" "$TMP_LOG"
grep -q "RUNTIME_RISK_REGIME_ROW" "$TMP_LOG"
grep -q "RUNTIME_RISK_REGIME_REASON_ROW" "$TMP_LOG"
grep -q "RUNTIME_RISK_REGIME_STATS_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_RISK_REGIME_STATS_V1_OK"
