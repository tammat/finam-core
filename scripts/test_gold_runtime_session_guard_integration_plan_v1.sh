#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_integration_plan_v1.py

src/scripts/research/build_gold_runtime_session_guard_integration_plan_v1.py \
  | tee /tmp/gold_runtime_session_guard_integration_plan_v1.out

grep -q "GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_V1" \
  /tmp/gold_runtime_session_guard_integration_plan_v1.out

grep -q "INTEGRATION_CANDIDATE" \
  /tmp/gold_runtime_session_guard_integration_plan_v1.out

grep -q "RULE=symbol in {GDU6@RTSX,GLU6@RTSX}" \
  /tmp/gold_runtime_session_guard_integration_plan_v1.out

grep -q "block_reason=gold_evening_session" \
  /tmp/gold_runtime_session_guard_integration_plan_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_READY" \
  /tmp/gold_runtime_session_guard_integration_plan_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_V1_OK"
