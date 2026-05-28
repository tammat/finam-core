#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

LOG_FILE="/tmp/runtime_guard_observability_replay_check_v1.log"

echo "TEST_RUNTIME_GUARD_OBSERVABILITY_REPLAY_CHECK_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/analytics/runtime_guard_config_loader_v1.py \
  src/finam_core/analytics/runtime_guard_decision_adapter_v1.py \
  src/finam_core/analytics/runtime_guard_observability_hook_v1.py

python - <<'PY' > "$LOG_FILE" 2>&1
from finam_core.analytics.runtime_guard_observability_hook_v1 import (
    RuntimeGuardObservabilityHookV1,
)

hook = RuntimeGuardObservabilityHookV1()

hook.observe_signal({
    "symbol": "BR_ROLLING@RTSX",
    "strategy": "HISTORICAL_BREAKOUT_V1",
    "timeframe": "M5",
    "features": {
        "regime": "UNKNOWN",
        "volatility_regime": "UNKNOWN",
        "session_type": "UNKNOWN",
    },
})
PY

grep -q "RUNTIME_GUARD_CONFIG_LOADED" "$LOG_FILE"
grep -q "RUNTIME_GUARD_LOOKUP" "$LOG_FILE"
grep -q "GUARD_DECISION_RUNTIME" "$LOG_FILE"
grep -q "RUNTIME_GUARD_OBSERVABILITY" "$LOG_FILE"
grep -q "decision=BLOCK" "$LOG_FILE"

cat "$LOG_FILE"

echo "TEST_RUNTIME_GUARD_OBSERVABILITY_REPLAY_CHECK_V1_OK"
