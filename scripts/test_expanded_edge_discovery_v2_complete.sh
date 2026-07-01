#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPANDED_EDGE_DISCOVERY_V2_COMPLETE ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/complete_expanded_edge_discovery_v2.py

OUT="$(PYTHONPATH=src python src/scripts/research/complete_expanded_edge_discovery_v2.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "expanded_runtime_candidate_rows="
echo "$OUT" | grep -q "runtime_or_execution_allowed_rows=0"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=EXPANDED_EDGE_DISCOVERY_V2_COMPLETE"

echo "VERDICT=TEST_EXPANDED_EDGE_DISCOVERY_V2_COMPLETE_OK"
