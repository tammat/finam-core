#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_shadow_failure_day_analysis_v1.py

python3 src/scripts/research/build_gold_shadow_failure_day_analysis_v1.py \
  | tee /tmp/gold_shadow_failure_day_analysis_v1.log

grep -q "GOLD SHADOW FAILURE DAY ANALYSIS V1" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "failure_day=2026-06-11" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "FAILURE_TRADE_ROW" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "MARKET_DAY_ROW" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "FAILURE_SUMMARY_ROW" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "classification=ALL_TRADES_LOST" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "runtime_allow=0" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "execution_enabled=0" /tmp/gold_shadow_failure_day_analysis_v1.log
grep -q "GOLD_SHADOW_FAILURE_DAY_ANALYSIS_V1_OK" /tmp/gold_shadow_failure_day_analysis_v1.log

echo TEST_GOLD_SHADOW_FAILURE_DAY_ANALYSIS_V1_OK
