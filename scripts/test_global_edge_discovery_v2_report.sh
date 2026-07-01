#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_DISCOVERY_V2_REPORT ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_global_edge_discovery_v2_report.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_global_edge_discovery_v2_report.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "universe_rows="
echo "$OUT" | grep -q "features_rows="
echo "$OUT" | grep -q "replay_rows="
echo "$OUT" | grep -q "ranking_rows="
echo "$OUT" | grep -q "forensic_rows="
echo "$OUT" | grep -q "robustness_rows="
echo "$OUT" | grep -q "walk_forward_rows="
echo "$OUT" | grep -q "runtime_candidate_rows="
echo "$OUT" | grep -q "runtime_or_execution_allowed_rows=0"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "orders_changed=0"
echo "$OUT" | grep -q "fills_changed=0"
echo "$OUT" | grep -q "VERDICT=GLOBAL_EDGE_DISCOVERY_V2_REPORT_READY"

echo "VERDICT=TEST_GLOBAL_EDGE_DISCOVERY_V2_REPORT_OK"
