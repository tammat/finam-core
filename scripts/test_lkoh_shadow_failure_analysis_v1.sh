#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_lkoh_shadow_failure_analysis_v1.py

python3 src/scripts/research/build_lkoh_shadow_failure_analysis_v1.py \
  | tee /tmp/lkoh_shadow_failure_analysis_v1.log

grep -q "LKOH SHADOW FAILURE ANALYSIS V1" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "SUMMARY_ROW" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "avg_win=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "avg_loss=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "largest_win=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "largest_loss=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "buy_expectancy=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "sell_expectancy=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "failure_mode=" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "runtime_allow=0" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "execution_enabled=0" /tmp/lkoh_shadow_failure_analysis_v1.log
grep -q "LKOH_SHADOW_FAILURE_ANALYSIS_V1_OK" /tmp/lkoh_shadow_failure_analysis_v1.log

echo TEST_LKOH_SHADOW_FAILURE_ANALYSIS_V1_OK
