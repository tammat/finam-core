#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_profit_factor_report_v1.py

python3 src/scripts/analytics/build_exit_reason_profit_factor_report_v1.py | \
  tee /tmp/exit_reason_profit_factor_report_v1.log

grep -q "EXIT REASON PROFIT FACTOR REPORT V1" /tmp/exit_reason_profit_factor_report_v1.log
grep -q "scope=trusted_window_only" /tmp/exit_reason_profit_factor_report_v1.log
grep -q "EXIT_REASON_RESULTS" /tmp/exit_reason_profit_factor_report_v1.log
grep -q "TRUSTED_ROWS=" /tmp/exit_reason_profit_factor_report_v1.log
grep -q "EXIT_REASON_PROFIT_FACTOR_REPORT_V1_OK" /tmp/exit_reason_profit_factor_report_v1.log

echo TEST_EXIT_REASON_PROFIT_FACTOR_REPORT_V1_OK
