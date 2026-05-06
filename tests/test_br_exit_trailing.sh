#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHONPATH=src .venv/bin/python - <<'PY'
from finam_core.risk.trailing_exit import TrailingExitEngine
from finam_core.strategy.exit_engine import ExitEngine

symbol = "BRM6@RTSX"

tr = TrailingExitEngine(stop_abs=0.30, take_abs=0.60, trail_abs=0.30)
tr.on_position_opened(symbol, 100.0)

assert tr.evaluate_long(symbol, 100.20, 1.0) is None
assert tr.evaluate_long(symbol, 100.40, 1.0) is None

state = tr.states[symbol]
assert state.max_price == 100.40, state
assert round(state.stop_loss, 2) == 100.10, state
print("BR_TRAILING_STOP_UPDATED_OK")

intent = tr.evaluate_long(symbol, 100.05, 1.0)
assert intent is not None, intent
assert intent["side"] == "SELL"
assert intent["reason"] == "TRAILING_STOP"
print("BR_TRAILING_STOP_EXIT_OK")

tr2 = TrailingExitEngine(stop_abs=0.30, take_abs=0.60, trail_abs=0.30)
tr2.on_position_opened(symbol, 100.0)

intent2 = tr2.evaluate_long(symbol, 100.60, 1.0)
assert intent2 is not None, intent2
assert intent2["side"] == "SELL"
assert intent2["reason"] == "TAKE_PROFIT"
print("BR_TAKE_PROFIT_EXIT_OK")

tr2.evaluate_long(symbol, 100.70, 0.0)
assert symbol not in tr2.states
print("BR_TRAILING_RESET_OK")

ex = ExitEngine(max_bars_in_trade=20, breakeven_atr_k=1.0, trailing_atr_k=1.5, stall_atr_k=0.2)

d = ex.evaluate(side="BUY", entry_price=100.0, current_price=101.0, atr=1.0, bars_held=3)
assert d.should_exit is False, d
assert d.stop_price == 100.0, d
print("BR_EXIT_BREAKEVEN_OK")

d = ex.evaluate(side="BUY", entry_price=100.0, current_price=102.0, atr=1.0, bars_held=4, current_stop=100.0)
assert d.should_exit is False, d
assert d.stop_price == 100.5, d
print("BR_EXIT_ATR_TRAILING_OK")

d = ex.evaluate(side="BUY", entry_price=100.0, current_price=100.4, atr=1.0, bars_held=5, current_stop=100.5)
assert d.should_exit is True, d
assert d.reason == "stop_loss_long", d
print("BR_EXIT_STOP_HIT_OK")

d = ex.evaluate(side="BUY", entry_price=100.0, current_price=100.8, atr=1.0, bars_held=20)
assert d.should_exit is True, d
assert d.reason == "time_exit", d
print("BR_EXIT_TIME_EXIT_OK")

print("BR_EXIT_TRAILING_TEST_OK")
PY
