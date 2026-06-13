#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_usdrub_shadow_failure_analysis_v1.py

python3 src/scripts/research/build_usdrub_shadow_failure_analysis_v1.py \
  | tee /tmp/usdrub_shadow_failure_analysis_v1.log

grep -q "USDRUB SHADOW FAILURE ANALYSIS V1" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "SUMMARY_ROW" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "avg_win=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "avg_loss=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "largest_win=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "largest_loss=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "buy_expectancy=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "sell_expectancy=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "failure_mode=" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "runtime_allow=0" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "execution_enabled=0" /tmp/usdrub_shadow_failure_analysis_v1.log
grep -q "USDRUB_SHADOW_FAILURE_ANALYSIS_V1_OK" /tmp/usdrub_shadow_failure_analysis_v1.log

echo TEST_USDRUB_SHADOW_FAILURE_ANALYSIS_V1_OK
