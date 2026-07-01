#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_DISCOVERY_V2_RESULT_REVIEW ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/review_global_edge_discovery_v2_result.py

OUT="$(PYTHONPATH=src python src/scripts/research/review_global_edge_discovery_v2_result.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "TOP_RANKING"
echo "$OUT" | grep -q "RANK_ROW"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=GLOBAL_EDGE_DISCOVERY_V2_RESULT_REVIEW_READY"

echo "VERDICT=TEST_GLOBAL_EDGE_DISCOVERY_V2_RESULT_REVIEW_OK"
