#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RISK_EVENT_STATS_FINAL_CHECK_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_risk_event_stats_final_check_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RISK_EVENT_STATS_FINAL_CHECK_V1" "$TMP_LOG"
grep -q "RISK_EVENT_STATS_FINAL_CHECK_STATUS" "$TMP_LOG"
grep -q "RISK_EVENT_STATS_FINAL_CHECK_V1_OK" "$TMP_LOG"

python src/scripts/analytics/build_risk_event_stats_by_reason_v1.py
python src/scripts/analytics/build_risk_event_stats_by_symbol_v1.py
python src/scripts/analytics/build_risk_event_stats_by_strategy_v1.py
python src/scripts/analytics/build_risk_event_dashboard_v1.py
python src/scripts/analytics/build_risk_event_audit_final_healthcheck_v1.py

echo "TEST_RISK_EVENT_STATS_FINAL_CHECK_V1_OK"
