#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_filtered_runtime_candidate_audit_v1.py

src/scripts/research/build_gold_filtered_runtime_candidate_audit_v1.py \
  | tee /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_V1" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "AUDIT_ROW symbol=GDU6@RTSX" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "AUDIT_ROW symbol=GLU6@RTSX" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "core_ok=" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "fee_drag_ok=" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "recent_ok=" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -q "concentration_ok=" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

grep -Eq "VERDICT=GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_(READY|RESEARCH_ONLY)" \
  /tmp/gold_filtered_runtime_candidate_audit_v1.out

echo "TEST_GOLD_FILTERED_RUNTIME_CANDIDATE_AUDIT_V1_OK"
