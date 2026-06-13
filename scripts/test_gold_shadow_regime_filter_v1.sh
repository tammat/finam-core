#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_shadow_regime_filter_v1.py

python3 src/scripts/research/build_gold_shadow_regime_filter_v1.py \
  | tee /tmp/gold_shadow_regime_filter_v1.log

grep -q "GOLD SHADOW REGIME FILTER V1" /tmp/gold_shadow_regime_filter_v1.log
grep -q "SUMMARY_ROW" /tmp/gold_shadow_regime_filter_v1.log
grep -q "runtime_allow=0" /tmp/gold_shadow_regime_filter_v1.log
grep -q "execution_enabled=0" /tmp/gold_shadow_regime_filter_v1.log
grep -q "GOLD_SHADOW_REGIME_FILTER_V1_OK" /tmp/gold_shadow_regime_filter_v1.log

echo TEST_GOLD_SHADOW_REGIME_FILTER_V1_OK
