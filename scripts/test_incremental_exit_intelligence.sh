#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.incremental_exit_intelligence import (
    IncrementalExitInput,
    build_incremental_exit_advice,
)

advice = build_incremental_exit_advice(
    IncrementalExitInput(
        symbol="BRM6@RTSX",
        strategy="br_conservative_breakout",
        timeframe="M5",
        side="BUY",
        entry_price=100.0,
        current_price=100.45,
        qty=1.0,
        take_distance=0.5,
        stop_distance=-0.4,
    )
)

assert advice.take_price == 100.5
assert advice.stop_price == 99.6
assert advice.action in {"NEAR_TAKE", "HOLD"}

stop = build_incremental_exit_advice(
    IncrementalExitInput(
        symbol="BRM6@RTSX",
        strategy="br_conservative_breakout",
        timeframe="M5",
        side="BUY",
        entry_price=100.0,
        current_price=99.55,
        qty=1.0,
        take_distance=0.5,
        stop_distance=-0.4,
    )
)

assert stop.action == "STOP_ZONE"

print("TEST_INCREMENTAL_EXIT_INTELLIGENCE_OK")
PY

python -m py_compile \
  src/finam_core/analytics/incremental_exit_intelligence.py \
  src/scripts/incremental_exit_intelligence.py
