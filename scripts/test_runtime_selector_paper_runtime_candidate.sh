#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_strategy_selector.py

grep -q "PAPER_RUNTIME_CANDIDATE" \
  src/finam_core/runtime/runtime_strategy_selector.py

python - <<'PY'
from finam_core.runtime.runtime_strategy_selector import (
    RuntimeStrategyCandidate,
    select_runtime_strategy,
)

r = select_runtime_strategy(
    RuntimeStrategyCandidate(
        symbol="NGF6@RTSX",
        strategy="NG_CONSERVATIVE_BREAKOUT_M1",
        timeframe="M1",
        trade_source="paper",
        runtime_action="PAPER_RUNTIME_CANDIDATE",
        allow_paper_signal=True,
        allow_radar_signal=True,
        allow_real_suggestion=False,
    )
)

assert r.enabled is True
assert r.mode == "PAPER_ENABLED"

print("TEST_RUNTIME_SELECTOR_PAPER_RUNTIME_CANDIDATE_OK")
PY
