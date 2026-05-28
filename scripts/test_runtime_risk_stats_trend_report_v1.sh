#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_RISK_STATS_TREND_REPORT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_risk_stats_trend_report_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_RISK_STATS_TREND_REPORT_V1" "$TMP_LOG"
grep -q "RUNTIME_RISK_STATS_TREND_STATUS" "$TMP_LOG"
grep -q "RUNTIME_RISK_STATS_TREND_ROW" "$TMP_LOG"
grep -q "RUNTIME_RISK_STATS_TREND_REASON_ROW" "$TMP_LOG"
grep -q "RUNTIME_RISK_STATS_TREND_REPORT_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_RISK_STATS_TREND_REPORT_V1_OK"
