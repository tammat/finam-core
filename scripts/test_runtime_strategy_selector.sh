#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.runtime_strategy_selector import (
    RuntimeStrategyCandidate,
    select_runtime_strategy,
)

promoted = select_runtime_strategy(
    RuntimeStrategyCandidate(
        symbol="BRM6@RTSX",
        strategy="br_conservative_breakout",
        timeframe="M5",
        trade_source="paper",
        runtime_action="PROMOTE",
        allow_paper_signal=True,
        allow_radar_signal=True,
        allow_real_suggestion=False,
    )
)
assert promoted.mode == "PAPER_ENABLED"
assert promoted.enabled is True

watch = select_runtime_strategy(
    RuntimeStrategyCandidate(
        symbol="PLZL@MISX",
        strategy="MOEX_MEAN_REVERSION_V1",
        timeframe="D1",
        trade_source="paper",
        runtime_action="WATCH",
        allow_paper_signal=False,
        allow_radar_signal=True,
        allow_real_suggestion=False,
    )
)
assert watch.mode == "RADAR_ONLY"
assert watch.enabled is True

blocked = select_runtime_strategy(
    RuntimeStrategyCandidate(
        symbol="PLZL@MISX",
        strategy="MOEX_SIMPLE_MOMENTUM",
        timeframe="D1",
        trade_source="paper",
        runtime_action="BLOCK",
        allow_paper_signal=False,
        allow_radar_signal=False,
        allow_real_suggestion=False,
    )
)
assert blocked.mode == "BLOCKED"
assert blocked.enabled is False

print("TEST_RUNTIME_STRATEGY_SELECTOR_OK")
PY

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_selector.py \
  src/scripts/build_runtime_strategy_selection.py
