#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPANDED_EDGE_DISCOVERY_V2_REPORT ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/build_expanded_edge_discovery_v2_report.py

OUT="$(PYTHONPATH=src python src/scripts/research/build_expanded_edge_discovery_v2_report.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "expanded_features_rows="
echo "$OUT" | grep -q "expanded_runtime_candidate_rows="
echo "$OUT" | grep -q "runtime_or_execution_allowed_rows=0"
echo "$OUT" | grep -q "TOP_50"
echo "$OUT" | grep -q "TOP_ROW"
echo "$OUT" | grep -q "runtime_allowed=0"
echo "$OUT" | grep -q "execution_allowed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "VERDICT=EXPANDED_EDGE_DISCOVERY_V2_REPORT_READY"

echo "VERDICT=TEST_EXPANDED_EDGE_DISCOVERY_V2_REPORT_OK"
