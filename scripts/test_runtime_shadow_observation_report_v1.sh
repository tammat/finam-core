#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_SHADOW_OBSERVATION_REPORT_V1_START"

python -m py_compile \
  src/finam_core/analytics/runtime_shadow_observation_v1.py \
  src/scripts/analytics/build_runtime_shadow_observation_report_v1.py

python - <<'PY'
from finam_core.analytics.runtime_shadow_observation_v1 import RuntimeShadowObservationV1

observer = RuntimeShadowObservationV1()

healthy = observer.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=8,
    expectancy_points=0.218,
    pnl_points=84.11,
    closed_trades=46,
)

decay = observer.evaluate(
    symbol="BR_ROLLING@RTSX",
    side="BUY",
    hour_msk=19,
    expectancy_points=-0.0486,
    pnl_points=-92.75,
    closed_trades=86,
)

print("SHADOW_HEALTHY", healthy.decay_state, healthy.shadow_block_candidate)
print("SHADOW_DECAY", decay.decay_state, decay.shadow_block_candidate)

assert healthy.shadow_block_candidate is False
assert decay.shadow_block_candidate is True

print("RUNTIME_SHADOW_OBSERVER_RUNTIME_OK")
PY

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_runtime_shadow_observation_report_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "RUNTIME_SHADOW_OBSERVATION_REPORT_V1" "$TMP_LOG"
grep -q "RUNTIME_SHADOW_OBSERVATION_ROW" "$TMP_LOG"
grep -q "RUNTIME_SHADOW_OBSERVATION_STATUS" "$TMP_LOG"
grep -q "RUNTIME_SHADOW_OBSERVATION_REPORT_V1_OK" "$TMP_LOG"

echo "TEST_RUNTIME_SHADOW_OBSERVATION_REPORT_V1_OK"
