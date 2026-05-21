#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=src

python -m py_compile src/finam_core/strategy/exit_engine.py

python - <<'PY'
from finam_core.strategy.exit_engine import ExitEngine

e = ExitEngine(max_bars_in_trade=20)

d = e.evaluate(
    side="BUY",
    entry_price=100,
    current_price=103,
    atr=2,
    bars_held=5,
    prev_close=102.0,
)
assert d.should_exit is False
assert d.stop_price is not None
assert d.stop_price >= 100

d = e.evaluate(
    side="BUY",
    entry_price=100,
    current_price=101,
    atr=2,
    bars_held=20,
)
assert d.should_exit is True
assert d.reason == "time_exit"

d = e.evaluate(
    side="SELL",
    entry_price=100,
    current_price=97,
    atr=2,
    bars_held=5,
    prev_close=96.0,
)
assert d.should_exit is False
assert d.stop_price is not None
assert d.stop_price <= 100

d = e.evaluate(
    side="SELL",
    entry_price=100,
    current_price=101,
    atr=2,
    bars_held=5,
    current_stop=100.5,
)
assert d.should_exit is True
assert d.reason == "stop_loss_short"

print("EXIT_ENGINE_TEST_OK")
PY
