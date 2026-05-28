#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

export PYTHONPATH=src

echo "TEST_RISK_EVENT_STATS_BY_REASON_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_risk_event_stats_by_reason_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RISK_EVENT_STATS_BY_REASON_V1" "$TMP_LOG"
grep -q "RISK_EVENT_STATS_BY_REASON_SUMMARY" "$TMP_LOG"
grep -q "RISK_EVENT_STATS_BY_REASON_ROW" "$TMP_LOG"
grep -q "RISK_EVENT_STATS_BY_REASON_V1_OK" "$TMP_LOG"

echo "TEST_RISK_EVENT_STATS_BY_REASON_V1_OK"
