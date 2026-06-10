#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_brn6_regime_shift_analysis_v1.py

python3 src/scripts/analytics/build_brn6_regime_shift_analysis_v1.py \
  | tee /tmp/brn6_regime_shift_analysis_v1.log

grep -q "BRN6 REGIME SHIFT ANALYSIS V1" \
  /tmp/brn6_regime_shift_analysis_v1.log

grep -q "CONTRACT_ROWS" \
  /tmp/brn6_regime_shift_analysis_v1.log

grep -q "SIDE_ROWS" \
  /tmp/brn6_regime_shift_analysis_v1.log

grep -q "REGIME_SHIFT_ROW" \
  /tmp/brn6_regime_shift_analysis_v1.log

grep -q "BRN6_REGIME_SHIFT_ANALYSIS_V1_OK" \
  /tmp/brn6_regime_shift_analysis_v1.log

echo "TEST_BRN6_REGIME_SHIFT_ANALYSIS_V1_OK"
