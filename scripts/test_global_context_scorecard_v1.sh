#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_CONTEXT_SCORECARD_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_context_scorecard_v1.py

src/scripts/research/build_global_context_scorecard_v1.py \
  | tee /tmp/global_context_scorecard_v1.out

grep -q "GLOBAL_CONTEXT_SCORECARD_V1" /tmp/global_context_scorecard_v1.out
grep -q "GLOBAL_CONTEXT_SCORECARD_ROWS" /tmp/global_context_scorecard_v1.out
grep -q "rows_total=" /tmp/global_context_scorecard_v1.out
grep -q "positive_rows=" /tmp/global_context_scorecard_v1.out
grep -q "research_candidates=" /tmp/global_context_scorecard_v1.out
grep -q "micro_live_candidates=0" /tmp/global_context_scorecard_v1.out
grep -q "next=GLOBAL_EDGE_DISCOVERY_V1" /tmp/global_context_scorecard_v1.out
grep -q "VERDICT=GLOBAL_CONTEXT_SCORECARD_READY" /tmp/global_context_scorecard_v1.out

echo "TEST_GLOBAL_CONTEXT_SCORECARD_V1_OK"
