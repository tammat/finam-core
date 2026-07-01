#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/review_expanded_edge_discovery_v2_result.py

OUT="$(PYTHONPATH=src python src/scripts/research/review_expanded_edge_discovery_v2_result.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "analytics_global_edge_expanded_features_v2.status="
echo "$OUT" | grep -q "analytics_global_edge_expanded_runtime_candidates_v2.candidate_status="
echo "$OUT" | grep -q "diagnosis=expanded_search_completed_runtime_blocked"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW_READY"

echo "VERDICT=TEST_EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW_OK"
