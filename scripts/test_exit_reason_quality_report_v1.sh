#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_exit_reason_quality_report_v1.py

python3 src/scripts/analytics/build_exit_reason_quality_report_v1.py \
  --root NG \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-03 00:00:00+00" \
  --group-by exit_reason,hour_msk,hold_bucket,side \
  | tee /tmp/exit_reason_quality_report_v1_ng.log

grep -q "EXIT REASON QUALITY REPORT V1" /tmp/exit_reason_quality_report_v1_ng.log
grep -q "report=parametric" /tmp/exit_reason_quality_report_v1_ng.log
grep -q "QUALITY_ROWS" /tmp/exit_reason_quality_report_v1_ng.log
grep -q "EXIT_REASON_QUALITY_REPORT_V1_OK" /tmp/exit_reason_quality_report_v1_ng.log

python3 src/scripts/analytics/build_exit_reason_quality_report_v1.py \
  --root BR \
  --source closed_trade_engine_v1_1 \
  --trusted-from "2026-06-05 00:00:00+00" \
  --group-by exit_reason,hour_msk,hold_bucket,side \
  | tee /tmp/exit_reason_quality_report_v1_br.log

grep -q "EXIT_REASON_QUALITY_REPORT_V1_OK" /tmp/exit_reason_quality_report_v1_br.log

echo TEST_EXIT_REASON_QUALITY_REPORT_V1_OK
