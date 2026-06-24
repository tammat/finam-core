#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_final_readiness_v1.py

src/scripts/research/build_gold_runtime_session_guard_final_readiness_v1.py \
  | tee /tmp/gold_runtime_session_guard_final_readiness_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V1" \
  /tmp/gold_runtime_session_guard_final_readiness_v1.out

grep -q "CHECK name=paper_pipeline_exists ok=1" \
  /tmp/gold_runtime_session_guard_final_readiness_v1.out

grep -q "CHECK name=insertion_point_unique ok=1" \
  /tmp/gold_runtime_session_guard_final_readiness_v1.out

grep -q "CHECK name=gold_guard_not_already_applied ok=1" \
  /tmp/gold_runtime_session_guard_final_readiness_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_READY_FOR_APPLY" \
  /tmp/gold_runtime_session_guard_final_readiness_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V1_OK"
