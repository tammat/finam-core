#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
src/scripts/research/build_gold_baseline_signal_research_v1.py

python3 \
src/scripts/research/build_gold_baseline_signal_research_v1.py \
| tee /tmp/gold_baseline_signal_research_v1.log

grep -q "GOLD BASELINE SIGNAL RESEARCH V1" \
/tmp/gold_baseline_signal_research_v1.log

grep -q "BASELINE_ROW" \
/tmp/gold_baseline_signal_research_v1.log

grep -q "GOLD_BASELINE_SIGNAL_RESEARCH_V1_OK" \
/tmp/gold_baseline_signal_research_v1.log

echo TEST_GOLD_BASELINE_SIGNAL_RESEARCH_V1_OK
