#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_EXIT_ENGINE_STALL_GUARD_V1_START"

"$PY_BIN" -m py_compile src/finam_core/strategy/exit_engine.py

"$PY_BIN" <<'PY'
from finam_core.strategy.exit_engine import ExitEngine

engine = ExitEngine(min_bars_before_stall_exit=3)

early = engine.evaluate(
    side="BUY",
    entry_price=3.245,
    current_price=3.246,
    atr=0.009,
    bars_held=0,
    prev_close=3.246,
    current_stop=3.02,
)

assert early.should_exit is False, early
assert early.reason == "hold_long", early

late = engine.evaluate(
    side="BUY",
    entry_price=3.245,
    current_price=3.246,
    atr=0.009,
    bars_held=3,
    prev_close=3.246,
    current_stop=3.02,
)

assert late.should_exit is True, late
assert late.reason == "stall_exit_long", late

print("EXIT_ENGINE_STALL_GUARD_ASSERTS_OK")
PY

grep -q "min_bars_before_stall_exit" src/finam_core/strategy/exit_engine.py

echo "TEST_EXIT_ENGINE_STALL_GUARD_V1_OK"
