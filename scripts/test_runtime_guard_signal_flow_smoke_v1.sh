#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_SIGNAL_FLOW_SMOKE_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/analytics/runtime_guard_config_loader_v1.py \
  src/finam_core/analytics/runtime_guard_decision_adapter_v1.py \
  src/finam_core/analytics/runtime_guard_observability_hook_v1.py \
  src/finam_core/analytics/runtime_guard_soft_block_mode_v1.py

grep -q "runtime_guard_soft_block_mode_v1" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RUNTIME_GUARD_SOFT_BLOCK_FAILED" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "runtime_guard_observability_hook_v1" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RUNTIME_GUARD_OBSERVABILITY_FAILED" \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from finam_core.analytics.runtime_guard_soft_block_mode_v1 import RuntimeGuardSoftBlockModeV1
from finam_core.analytics.runtime_guard_observability_hook_v1 import RuntimeGuardObservabilityHookV1

intent = {
    "symbol": "BR_ROLLING@RTSX",
    "strategy": "HISTORICAL_BREAKOUT_V1",
    "timeframe": "M5",
    "features": {
        "regime": "UNKNOWN",
        "volatility_regime": "UNKNOWN",
        "session_type": "UNKNOWN",
    },
}

soft_block = RuntimeGuardSoftBlockModeV1()
soft_decision = soft_block.apply(intent)

assert soft_decision.decision == "BLOCK"
assert intent["features"]["runtime_guard_decision"] == "BLOCK"
assert intent["features"]["runtime_soft_blocked"] is True

hook = RuntimeGuardObservabilityHookV1()
obs_decision = hook.observe_signal(intent)

assert obs_decision.decision == "BLOCK"
assert obs_decision.matched is True

print("RUNTIME_GUARD_SIGNAL_FLOW_SMOKE_V1_PY_OK")
PY

echo "TEST_RUNTIME_GUARD_SIGNAL_FLOW_SMOKE_V1_OK"
