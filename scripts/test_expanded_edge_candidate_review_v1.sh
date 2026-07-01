#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPANDED_EDGE_CANDIDATE_REVIEW_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/review_expanded_edge_candidates_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/review_expanded_edge_candidates_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "research_candidates="
echo "$OUT" | grep -q "top_rows="
echo "$OUT" | grep -q "CANDIDATE_ROW"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=EXPANDED_EDGE_CANDIDATE_REVIEW_V1_READY"

echo "VERDICT=TEST_EXPANDED_EDGE_CANDIDATE_REVIEW_V1_OK"
