#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_replay_v2_hour_range_compare.py

python3 src/scripts/research/build_gold_replay_v2_hour_range_compare.py \
  | tee /tmp/gold_replay_v2_hour_range_compare.log

grep -q "GOLD REPLAY V2 HOUR RANGE COMPARE" /tmp/gold_replay_v2_hour_range_compare.log
grep -q "RANGE_ROWS" /tmp/gold_replay_v2_hour_range_compare.log
grep -q "RANGE_ROW range=HOUR_16" /tmp/gold_replay_v2_hour_range_compare.log
grep -q "RANGE_ROW range=HOURS_15_18" /tmp/gold_replay_v2_hour_range_compare.log
grep -q "BEST_RANGE" /tmp/gold_replay_v2_hour_range_compare.log
grep -q "GOLD_REPLAY_V2_HOUR_RANGE_COMPARE_OK" /tmp/gold_replay_v2_hour_range_compare.log

echo "TEST_GOLD_REPLAY_V2_HOUR_RANGE_COMPARE_OK"
