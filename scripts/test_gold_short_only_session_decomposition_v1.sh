#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_gold_short_only_session_decomposition_v1.py

python3 src/scripts/research/build_gold_short_only_session_decomposition_v1.py \
  | tee /tmp/gold_short_only_session_decomposition_v1.log

grep -q "GOLD SHORT ONLY SESSION DECOMPOSITION V1" /tmp/gold_short_only_session_decomposition_v1.log
grep -q "SESSION_ROWS" /tmp/gold_short_only_session_decomposition_v1.log
grep -q "HOUR_ROWS" /tmp/gold_short_only_session_decomposition_v1.log
grep -q "TOTAL_ROW" /tmp/gold_short_only_session_decomposition_v1.log
grep -q "GOLD_SHORT_ONLY_SESSION_DECOMPOSITION_V1_OK" /tmp/gold_short_only_session_decomposition_v1.log

echo "TEST_GOLD_SHORT_ONLY_SESSION_DECOMPOSITION_V1_OK"
