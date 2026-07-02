#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPANDED_EDGE_TOP3_FORENSIC_DEEP_DIVE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_expanded_edge_top3_forensic_deep_dive_v1.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_expanded_edge_top3_forensic_deep_dive_v1.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "TOP1"
echo "$OUT" | grep -q "TOP2"
echo "$OUT" | grep -q "TOP3"
echo "$OUT" | grep -q "FINAL_VERDICT="
echo "$OUT" | grep -q "summary_top3=3"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=EXPANDED_EDGE_TOP3_FORENSIC_DEEP_DIVE_V1_READY"

echo "VERDICT=TEST_EXPANDED_EDGE_TOP3_FORENSIC_DEEP_DIVE_V1_OK"
