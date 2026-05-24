#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_selector.py \
  src/finam_core/runtime/strategy_lifecycle_state_machine.py

python - <<'PY'
from finam_core.runtime.runtime_strategy_selector import RuntimeStrategyCandidate, select_runtime_strategy
from finam_core.runtime.strategy_lifecycle_state_machine import StrategyLifecycleInput, decide_strategy_lifecycle

selection = select_runtime_strategy(
    RuntimeStrategyCandidate(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        trade_source="paper",
        runtime_action="RESEARCH_WATCH",
        allow_paper_signal=False,
        allow_radar_signal=True,
        allow_real_suggestion=False,
    )
)

assert selection.mode == "RESEARCH_WATCH"
assert selection.enabled is False

lifecycle = decide_strategy_lifecycle(
    StrategyLifecycleInput(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        runtime_action="RESEARCH_WATCH",
        score=35.0,
        rank_status="WATCH_DIVERGENCE",
    )
)

assert lifecycle.lifecycle_state == "RESEARCH_WATCH"
assert lifecycle.allow_runtime is False
assert lifecycle.allow_radar is True
assert lifecycle.allow_research is True

print("RESEARCH_WATCH_RUNTIME_LIFECYCLE_UNIT_OK")
PY

grep -q "RESEARCH_WATCH" src/finam_core/runtime/runtime_strategy_selector.py
grep -q "RESEARCH_WATCH" src/finam_core/runtime/strategy_lifecycle_state_machine.py

echo "RESEARCH_WATCH_RUNTIME_LIFECYCLE_TEST_OK"
