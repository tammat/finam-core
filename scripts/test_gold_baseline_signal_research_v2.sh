#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_baseline_signal_research_v2.py

python3 src/scripts/research/build_gold_baseline_signal_research_v2.py \
  | tee /tmp/gold_baseline_signal_research_v2.log

grep -q "GOLD BASELINE SIGNAL RESEARCH V2" /tmp/gold_baseline_signal_research_v2.log
grep -q "ALL_ROW" /tmp/gold_baseline_signal_research_v2.log
grep -q "LONG_ROW" /tmp/gold_baseline_signal_research_v2.log
grep -q "SHORT_ROW" /tmp/gold_baseline_signal_research_v2.log
grep -q "COMPARISON_ROW" /tmp/gold_baseline_signal_research_v2.log
grep -q "GOLD_BASELINE_SIGNAL_RESEARCH_V2_OK" /tmp/gold_baseline_signal_research_v2.log

echo "TEST_GOLD_BASELINE_SIGNAL_RESEARCH_V2_OK"
