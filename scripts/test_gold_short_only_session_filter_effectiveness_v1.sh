#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_short_only_session_filter_effectiveness_v1.py

python3 src/scripts/research/build_gold_short_only_session_filter_effectiveness_v1.py \
  | tee /tmp/gold_short_only_session_filter_effectiveness_v1.log

grep -q "GOLD SHORT ONLY SESSION FILTER EFFECTIVENESS V1" /tmp/gold_short_only_session_filter_effectiveness_v1.log
grep -q "FILTER_EFFECTIVENESS_ROWS" /tmp/gold_short_only_session_filter_effectiveness_v1.log
grep -q "KEEP_ROW" /tmp/gold_short_only_session_filter_effectiveness_v1.log
grep -q "AVOID_ROW" /tmp/gold_short_only_session_filter_effectiveness_v1.log
grep -q "EFFECTIVENESS_ROW" /tmp/gold_short_only_session_filter_effectiveness_v1.log
grep -q "GOLD_SHORT_ONLY_SESSION_FILTER_EFFECTIVENESS_V1_OK" /tmp/gold_short_only_session_filter_effectiveness_v1.log

echo "TEST_GOLD_SHORT_ONLY_SESSION_FILTER_EFFECTIVENESS_V1_OK"
