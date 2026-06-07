#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/analytics/exit_reason_trusted_window_policy_v1.py \
  src/scripts/analytics/build_exit_reason_trusted_coverage_report_v1.py

python3 src/scripts/analytics/build_exit_reason_trusted_coverage_report_v1.py | \
  tee /tmp/exit_reason_trusted_coverage_report_v1.log

grep -q "EXIT REASON TRUSTED COVERAGE REPORT V1" /tmp/exit_reason_trusted_coverage_report_v1.log
grep -q "TRUSTED_ROOT_COVERAGE" /tmp/exit_reason_trusted_coverage_report_v1.log
grep -q "TRUSTED_SYMBOL_COVERAGE" /tmp/exit_reason_trusted_coverage_report_v1.log
grep -q "TRUSTED_EXIT_REASON_DISTRIBUTION" /tmp/exit_reason_trusted_coverage_report_v1.log
grep -q "TRUSTED_EXIT_REASON_QUALITY" /tmp/exit_reason_trusted_coverage_report_v1.log
grep -q "EXIT_REASON_TRUSTED_COVERAGE_REPORT_V1_OK" /tmp/exit_reason_trusted_coverage_report_v1.log

echo TEST_EXIT_REASON_TRUSTED_COVERAGE_REPORT_V1_OK
