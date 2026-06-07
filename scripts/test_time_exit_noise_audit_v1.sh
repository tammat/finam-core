#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

test -f src/scripts/analytics/build_time_exit_noise_audit_v1.py

python3 -m py_compile src/scripts/analytics/build_time_exit_noise_audit_v1.py

python3 src/scripts/analytics/build_time_exit_noise_audit_v1.py | \
  tee /tmp/time_exit_noise_audit_v1.log

grep -q "TIME EXIT NOISE AUDIT V1" /tmp/time_exit_noise_audit_v1.log
grep -q "CLOSED_TRADE_QUALITY_BY_ROOT_SIDE" /tmp/time_exit_noise_audit_v1.log
grep -q "EXIT_EVENT_REASON_SUMMARY_FROM_TRADES" /tmp/time_exit_noise_audit_v1.log
grep -q "TIME_EXIT_ANALYSIS" /tmp/time_exit_noise_audit_v1.log
grep -q "TIME_EXIT_DUPLICATE_AUDIT" /tmp/time_exit_noise_audit_v1.log
grep -q "TIME_EXIT_NOISE_AUDIT_V1_OK" /tmp/time_exit_noise_audit_v1.log

echo TEST_TIME_EXIT_NOISE_AUDIT_V1_OK
