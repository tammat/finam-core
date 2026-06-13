#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_rollover_status_report_v1.py

python3 src/scripts/analytics/build_rollover_status_report_v1.py \
  | tee /tmp/rollover_status_report_v1.log

grep -q "ROLLOVER STATUS REPORT V1" /tmp/rollover_status_report_v1.log
grep -q "ROLLOVER_ROWS" /tmp/rollover_status_report_v1.log
grep -q "ROLLOVER_STATUS_REPORT_V1_OK" /tmp/rollover_status_report_v1.log

echo "TEST_ROLLOVER_STATUS_REPORT_V1_OK"
