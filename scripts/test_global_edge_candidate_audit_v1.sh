#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_EDGE_CANDIDATE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_edge_candidate_audit_v1.py

src/scripts/research/build_global_edge_candidate_audit_v1.py \
  | tee /tmp/global_edge_candidate_audit_v1.out

grep -q "GLOBAL_EDGE_CANDIDATE_AUDIT_V1" /tmp/global_edge_candidate_audit_v1.out
grep -q "CANDIDATE_ROWS" /tmp/global_edge_candidate_audit_v1.out
grep -q "candidate_rows=1" /tmp/global_edge_candidate_audit_v1.out
grep -q "micro_live_candidates=0" /tmp/global_edge_candidate_audit_v1.out
grep -q "promotion_allowed=0" /tmp/global_edge_candidate_audit_v1.out
grep -q "next=GLOBAL_EDGE_CANDIDATE_REGISTRY_SEED_V1" /tmp/global_edge_candidate_audit_v1.out
grep -q "VERDICT=GLOBAL_EDGE_CANDIDATE_AUDIT_READY" /tmp/global_edge_candidate_audit_v1.out

echo "TEST_GLOBAL_EDGE_CANDIDATE_AUDIT_V1_OK"
