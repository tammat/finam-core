#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_short_only_research_v1.py

python3 src/scripts/research/build_gold_short_only_research_v1.py \
  | tee /tmp/gold_short_only_research_v1.log

grep -q "GOLD SHORT ONLY RESEARCH V1" /tmp/gold_short_only_research_v1.log
grep -q "SHORT_ONLY_ROWS" /tmp/gold_short_only_research_v1.log
grep -q "SHORT_ONLY_ROW symbol=GDM6@RTSX" /tmp/gold_short_only_research_v1.log
grep -q "SHORT_ONLY_ROW symbol=GDU6@RTSX" /tmp/gold_short_only_research_v1.log
grep -q "GOLD_SHORT_ONLY_RESEARCH_V1_OK" /tmp/gold_short_only_research_v1.log

echo "TEST_GOLD_SHORT_ONLY_RESEARCH_V1_OK"
