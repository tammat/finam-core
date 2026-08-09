#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE EDGE SEARCH NEAR READY V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_edge_search_near_ready_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_universe_edge_search_near_ready_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=research_read_only' \
  <<< "$OUTPUT"

grep -q \
  'readiness_policy_changed=0' \
  <<< "$OUTPUT"

grep -q 'NEAR_READY_ROWS' <<< "$OUTPUT"
grep -q 'BLOCK_REASON_ROWS' <<< "$OUTPUT"
grep -q 'SUMMARY_ROW' <<< "$OUTPUT"

grep -q \
  'strategy_search_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'edge_probability_calculated=0' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -q \
  'VERDICT=UNIVERSE_EDGE_SEARCH_NEAR_READY_V1_READY' \
  <<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_EDGE_SEARCH_NEAR_READY_V1_OK"
