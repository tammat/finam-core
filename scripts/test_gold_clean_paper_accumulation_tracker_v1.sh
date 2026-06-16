#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_gold_clean_paper_accumulation_tracker_v1.py

python3 src/scripts/research/build_gold_clean_paper_accumulation_tracker_v1.py \
  | tee /tmp/gold_clean_paper_accumulation_tracker_v1.log

grep -q "GOLD_CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK" /tmp/gold_clean_paper_accumulation_tracker_v1.log
grep -q "GOLD_SHADOW_REFERENCE_ROW" /tmp/gold_clean_paper_accumulation_tracker_v1.log
grep -q "GDU6@RTSX" /tmp/gold_clean_paper_accumulation_tracker_v1.log

if grep -q "runtime_allow=1" /tmp/gold_clean_paper_accumulation_tracker_v1.log; then
  echo "FAIL: runtime enabled in gold tracker"
  exit 1
fi

if grep -q "execution_enabled=1" /tmp/gold_clean_paper_accumulation_tracker_v1.log; then
  echo "FAIL: execution enabled in gold tracker"
  exit 1
fi

echo TEST_GOLD_CLEAN_PAPER_ACCUMULATION_TRACKER_V1_OK
