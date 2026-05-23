#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/ng_live_runtime_state_machine.py \
  src/scripts/build_ng_live_runtime_state.py

python - <<'PY'
from finam_core.runtime.ng_live_runtime_state_machine import (
    NgLiveRuntimeInput,
    NgLiveRuntimeStateMachine,
)

m = NgLiveRuntimeStateMachine()

d1 = m.decide(NgLiveRuntimeInput(
    symbol="NGF6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT_M1",
    timeframe="M1",
    previous_state="DISABLED",
    active_edge=True,
    governance_allow=True,
    market_data_fresh=True,
    open_position_qty=0,
))
assert d1.runtime_state == "WARMUP"
assert d1.allow_new_entries is False

d2 = m.decide(NgLiveRuntimeInput(
    symbol="NGF6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT_M1",
    timeframe="M1",
    previous_state="WARMUP",
    active_edge=True,
    governance_allow=True,
    market_data_fresh=True,
    open_position_qty=0,
))
assert d2.runtime_state == "ACTIVE"
assert d2.allow_new_entries is True

d3 = m.decide(NgLiveRuntimeInput(
    symbol="NGF6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT_M1",
    timeframe="M1",
    previous_state="ACTIVE",
    active_edge=False,
    governance_allow=True,
    market_data_fresh=True,
    open_position_qty=1,
))
assert d3.runtime_state == "EXIT_ONLY"
assert d3.allow_new_entries is False
assert d3.allow_position_management is True

print("TEST_NG_LIVE_RUNTIME_STATE_MACHINE_OK")
PY
