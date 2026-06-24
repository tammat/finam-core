#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_RUNTIME_SESSION_GUARD_SHADOW_RUNTIME_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_runtime_session_guard_shadow_runtime_validation_v1.py

src/scripts/research/build_gold_runtime_session_guard_shadow_runtime_validation_v1.py \
  | tee /tmp/gold_runtime_session_guard_shadow_runtime_validation_v1.out

grep -q "VERDICT=GOLD_RUNTIME_SESSION_GUARD_SHADOW_RUNTIME_VALIDATION_READY" \
  /tmp/gold_runtime_session_guard_shadow_runtime_validation_v1.out

echo "TEST_GOLD_RUNTIME_SESSION_GUARD_SHADOW_RUNTIME_VALIDATION_V1_OK"
