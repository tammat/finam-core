#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile src/finam_core/strategy/futures/ng_conservative_breakout.py

python - <<'PY'
from finam_core.strategy.futures.ng_conservative_breakout import NgConservativeBreakout

bars = []

price = 3.000
for i in range(30):
    bars.append({
        "open": price,
        "high": price + 0.005,
        "low": price - 0.005,
        "close": price,
    })
    price += 0.001

bars.append({
    "open": 3.030,
    "high": 3.080,
    "low": 3.025,
    "close": 3.075,
})

s = NgConservativeBreakout(symbol="NGM6@RTSX").on_bars(bars)

assert s is not None
assert s.side == "BUY"
assert s.strategy == "NG_CONSERVATIVE_BREAKOUT"
assert s.stop_price < s.entry_price
assert s.take_price > s.entry_price

print("TEST_NG_CONSERVATIVE_BREAKOUT_OK")
PY
