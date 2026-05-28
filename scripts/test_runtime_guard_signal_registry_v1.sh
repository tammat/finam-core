#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_SIGNAL_REGISTRY_V1_START"

python -m py_compile \
  src/finam_core/analytics/runtime_guard_signal_registry_v1.py \
  src/finam_core/analytics/runtime_guard_soft_block_mode_v1.py

python - <<'PY'
from finam_core.analytics.runtime_guard_soft_block_mode_v1 import RuntimeGuardSoftBlockModeV1
from finam_core.analytics.runtime_guard_signal_registry_v1 import RuntimeGuardSignalRegistryV1

signal = {
    "signal_id": "test-runtime-guard-registry-v1",
    "symbol": "BR_ROLLING@RTSX",
    "strategy": "HISTORICAL_BREAKOUT_V1",
    "timeframe": "M5",
    "qty": 1,
    "features": {
        "regime": "UNKNOWN",
        "volatility_regime": "UNKNOWN",
        "session_type": "UNKNOWN",
    },
}

soft_block = RuntimeGuardSoftBlockModeV1()
decision = soft_block.apply(signal)

registry = RuntimeGuardSignalRegistryV1()
registry.migrate()
registry.save(signal=signal, decision=decision)

print("RUNTIME_GUARD_SIGNAL_REGISTRY_V1_PY_OK")
PY

psql "$DATABASE_URL" -c "
select
  signal_id,
  symbol,
  strategy,
  timeframe,
  guard_decision,
  runtime_soft_blocked,
  guard_matched
from runtime_guard_signal_registry_v1
where signal_id = 'test-runtime-guard-registry-v1';
"

echo "TEST_RUNTIME_GUARD_SIGNAL_REGISTRY_V1_OK"
