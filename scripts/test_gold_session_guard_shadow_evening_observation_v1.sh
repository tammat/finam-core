#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GOLD_SESSION_GUARD_SHADOW_EVENING_OBSERVATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_gold_session_guard_shadow_evening_observation_v1.py

src/scripts/research/build_gold_session_guard_shadow_evening_observation_v1.py \
  | tee /tmp/gold_session_guard_shadow_evening_observation_v1.out

grep -q "VERDICT=GOLD_SESSION_GUARD_SHADOW_EVENING_OBSERVATION_READY" \
  /tmp/gold_session_guard_shadow_evening_observation_v1.out

echo "TEST_GOLD_SESSION_GUARD_SHADOW_EVENING_OBSERVATION_V1_OK"
