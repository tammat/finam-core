#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_helper_plan_v1.py

src/scripts/research/build_gold_runtime_session_guard_helper_plan_v1.py \
  | tee /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_V1" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "_resolve_hour_msk_v1" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "Europe/Moscow" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "new_tables=0" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "execution_change=0" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_READY" \
  /tmp/gold_runtime_session_guard_helper_plan_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_V1_OK"
