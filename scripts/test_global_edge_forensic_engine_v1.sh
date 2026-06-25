#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_FORENSIC_ENGINE_V1 ==="

src/scripts/research/build_global_edge_forensic_engine_v1.py \
  --candidate-id MSC-000001 \
  | tee /tmp/global_edge_forensic_engine_v1.out

grep -q "GLOBAL_EDGE_FORENSIC_ENGINE_V1" /tmp/global_edge_forensic_engine_v1.out
grep -q "candidate_id=MSC-000001" /tmp/global_edge_forensic_engine_v1.out
grep -q "replay_status=PASS" /tmp/global_edge_forensic_engine_v1.out
grep -q "runtime_changed=0" /tmp/global_edge_forensic_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/global_edge_forensic_engine_v1.out
grep -q "VERDICT=" /tmp/global_edge_forensic_engine_v1.out

echo "TEST_GLOBAL_EDGE_FORENSIC_ENGINE_V1_OK"
