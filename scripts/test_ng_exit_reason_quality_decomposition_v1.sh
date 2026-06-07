#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/scripts/analytics/build_ng_exit_reason_quality_decomposition_v1.py

python3 src/scripts/analytics/build_ng_exit_reason_quality_decomposition_v1.py | \
  tee /tmp/ng_exit_reason_quality_decomposition_v1.log

grep -q "NG EXIT REASON QUALITY DECOMPOSITION V1" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "EXIT_REASON_SUMMARY" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "EXIT_REASON_BY_HOUR_MSK" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "EXIT_REASON_BY_REGIME" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "EXIT_REASON_BY_HOLD_BUCKET" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "EXIT_REASON_BY_SIDE" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "TOP_LOSS_CLUSTERS" /tmp/ng_exit_reason_quality_decomposition_v1.log
grep -q "NG_EXIT_REASON_QUALITY_DECOMPOSITION_V1_OK" /tmp/ng_exit_reason_quality_decomposition_v1.log

echo TEST_NG_EXIT_REASON_QUALITY_DECOMPOSITION_V1_OK
