#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_EDGE_DISCOVERY_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_edge_discovery_v1.py

src/scripts/research/build_global_edge_discovery_v1.py \
  | tee /tmp/global_edge_discovery_v1.out

grep -q "GLOBAL_EDGE_DISCOVERY_V1" /tmp/global_edge_discovery_v1.out
grep -q "EDGE_DISCOVERY_ROWS" /tmp/global_edge_discovery_v1.out
grep -q "rows_total=" /tmp/global_edge_discovery_v1.out
grep -q "positive_rows=" /tmp/global_edge_discovery_v1.out
grep -q "research_candidates=" /tmp/global_edge_discovery_v1.out
grep -q "micro_live_candidates=0" /tmp/global_edge_discovery_v1.out
grep -q "DECISION" /tmp/global_edge_discovery_v1.out
grep -q "next=GLOBAL_EDGE_CANDIDATE_AUDIT_V1" /tmp/global_edge_discovery_v1.out
grep -q "VERDICT=GLOBAL_EDGE_DISCOVERY_READY" /tmp/global_edge_discovery_v1.out

echo "TEST_GLOBAL_EDGE_DISCOVERY_V1_OK"
