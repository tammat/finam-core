#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_SOFT_BLOCK_MODE_V1_START"

python -m py_compile \
  src/finam_core/analytics/runtime_guard_config_loader_v1.py \
  src/finam_core/analytics/runtime_guard_decision_adapter_v1.py \
  src/finam_core/analytics/runtime_guard_soft_block_mode_v1.py

python - <<'PY'
from finam_core.analytics.runtime_guard_soft_block_mode_v1 import RuntimeGuardSoftBlockModeV1

runtime = RuntimeGuardSoftBlockModeV1()

signal = {
    "symbol": "BR_ROLLING@RTSX",
    "strategy": "HISTORICAL_BREAKOUT_V1",
    "timeframe": "M5",
    "features": {
        "regime": "UNKNOWN",
        "volatility_regime": "UNKNOWN",
        "session_type": "UNKNOWN",
    },
}

decision = runtime.apply(signal)

assert decision.decision == "BLOCK"
assert signal["features"]["runtime_guard_decision"] == "BLOCK"
assert signal["features"]["runtime_soft_blocked"] is True

print("RUNTIME_GUARD_SOFT_BLOCK_MODE_V1_PY_OK")
PY

echo "TEST_RUNTIME_GUARD_SOFT_BLOCK_MODE_V1_OK"
