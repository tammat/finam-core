#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE EDGE SEARCH V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_edge_search_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python src/scripts/research/build_universe_edge_search_v1.py
)"

echo "$OUTPUT"

grep -q \
  'ranking=edge_search_readiness_not_edge_probability' \
  <<< "$OUTPUT"

grep -q \
  'UNIVERSE_READY_ROWS' \
  <<< "$OUTPUT"

grep -q \
  'SUMMARY_ROW' \
  <<< "$OUTPUT"

grep -q \
  'edge_probability_calculated=0' \
  <<< "$OUTPUT"

grep -q \
  'strategy_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'db_writes_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'execution_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'VERDICT=UNIVERSE_EDGE_SEARCH_V1_READY' \
  <<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo "VERDICT=TEST_UNIVERSE_EDGE_SEARCH_V1_OK"
