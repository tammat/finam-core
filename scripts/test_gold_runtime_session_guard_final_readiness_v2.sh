#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V2 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_final_readiness_v2.py

src/scripts/research/build_gold_runtime_session_guard_final_readiness_v2.py \
  | tee /tmp/gold_runtime_session_guard_final_readiness_v2.out

grep -q "target_line_exists ok=1" \
  /tmp/gold_runtime_session_guard_final_readiness_v2.out

grep -q "gold_guard_not_already_applied ok=1" \
  /tmp/gold_runtime_session_guard_final_readiness_v2.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_READY_FOR_APPLY" \
  /tmp/gold_runtime_session_guard_final_readiness_v2.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V2_OK"
