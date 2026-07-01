#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_DISCOVERY_V2_START ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/research/start_global_edge_discovery_v2.py

OUT="$(PYTHONPATH=src python src/scripts/research/start_global_edge_discovery_v2.py)"

echo "$OUT"

echo "$OUT" | grep -q "mode=research_only"
echo "$OUT" | grep -q "runtime_changed=0"
echo "$OUT" | grep -q "execution_changed=0"
echo "$OUT" | grep -q "micro_live_allowed=0"
echo "$OUT" | grep -q "dashboard_v1_required=1"
echo "$OUT" | grep -q "edge_pipeline=READY"
echo "$OUT" | grep -q "VERDICT=GLOBAL_EDGE_DISCOVERY_V2_START_READY"

echo "VERDICT=TEST_GLOBAL_EDGE_DISCOVERY_V2_START_OK"
