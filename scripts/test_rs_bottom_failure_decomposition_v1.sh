#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FAILURE_DECOMPOSITION_V1 ==="

python3 -m py_compile src/scripts/research/build_rs_bottom_failure_decomposition_v1.py

python3 src/scripts/research/build_rs_bottom_failure_decomposition_v1.py \
  | tee /tmp/rs_bottom_failure_decomposition_v1.log

grep -q "FILTER_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "SELECTION_FILTER_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "CONTRACT_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "HOUR_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "WORST_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "BEST_ROW" /tmp/rs_bottom_failure_decomposition_v1.log
grep -q "VERDICT=RS_BOTTOM_FAILURE_DECOMPOSITION_READY" /tmp/rs_bottom_failure_decomposition_v1.log

echo "VERDICT=RS_BOTTOM_FAILURE_DECOMPOSITION_TEST_OK"
echo "TEST_RS_BOTTOM_FAILURE_DECOMPOSITION_V1_OK"
