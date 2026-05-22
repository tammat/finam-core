#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.strategy_lifecycle_state_machine import (
    StrategyLifecycleInput,
    decide_strategy_lifecycle,
)

paper = decide_strategy_lifecycle(
    StrategyLifecycleInput(
        symbol="BRM6@RTSX",
        strategy="br_conservative_breakout",
        timeframe="M5",
        runtime_action="PROMOTE",
        score=50,
        rank_status="PROMISING",
    )
)
assert paper.lifecycle_state == "PAPER"
assert paper.allow_runtime is True

radar = decide_strategy_lifecycle(
    StrategyLifecycleInput(
        symbol="PLZL@MISX",
        strategy="MOEX_MEAN_REVERSION_V1",
        timeframe="D1",
        runtime_action="WATCH",
        score=13,
        rank_status="WATCH",
    )
)
assert radar.lifecycle_state == "RADAR"
assert radar.allow_runtime is False
assert radar.allow_radar is True

blocked = decide_strategy_lifecycle(
    StrategyLifecycleInput(
        symbol="PLZL@MISX",
        strategy="MOEX_SIMPLE_MOMENTUM",
        timeframe="D1",
        runtime_action="BLOCK",
        score=0,
        rank_status="REJECT",
    )
)
assert blocked.lifecycle_state == "BLOCKED"
assert blocked.allow_runtime is False

print("TEST_STRATEGY_LIFECYCLE_STATE_MACHINE_OK")
PY

python -m py_compile \
  src/finam_core/runtime/strategy_lifecycle_state_machine.py \
  src/finam_core/runtime/strategy_lifecycle_repository.py \
  src/scripts/build_strategy_lifecycle_state.py
