#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=src

python -m py_compile src/finam_core/strategy/ng_volatility_breakout.py

python - <<'PY'
from finam_core.strategy.ng_volatility_breakout import NgVolatilityBreakout

bars = []
price = 3.0
for i in range(30):
    bars.append({
        "open": price,
        "high": price + 0.02,
        "low": price - 0.02,
        "close": price,
    })

bars.append({
    "open": 3.0,
    "high": 3.12,
    "low": 2.99,
    "close": 3.12,
})

s = NgVolatilityBreakout()
sig = s.on_bars(bars)

assert sig is not None, "expected NG breakout signal"
assert sig.symbol == "NGK6@RTSX"
assert sig.side == "BUY"
assert sig.features["stop"] < sig.price
assert sig.features["take"] > sig.price

print("NG_STRATEGY_TEST_OK")
PY
