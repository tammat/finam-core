#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_coverage_audit_v1.py

python3 src/scripts/analytics/build_exit_reason_coverage_audit_v1.py | \
  tee /tmp/exit_reason_coverage_audit_v1.log

grep -q "EXIT REASON COVERAGE AUDIT V1" /tmp/exit_reason_coverage_audit_v1.log
grep -q "ROOT_COVERAGE" /tmp/exit_reason_coverage_audit_v1.log
grep -q "SOURCE_COVERAGE" /tmp/exit_reason_coverage_audit_v1.log
grep -q "SYMBOL_COVERAGE" /tmp/exit_reason_coverage_audit_v1.log
grep -q "DAY_COVERAGE" /tmp/exit_reason_coverage_audit_v1.log
grep -q "EXIT_REASON_DISTRIBUTION" /tmp/exit_reason_coverage_audit_v1.log
grep -q "EXIT_REASON_COVERAGE_AUDIT_V1_OK" /tmp/exit_reason_coverage_audit_v1.log

echo TEST_EXIT_REASON_COVERAGE_AUDIT_V1_OK
