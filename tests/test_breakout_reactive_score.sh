#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src STRATEGY_BREAKOUT_WINDOW=3 STRATEGY_BREAKOUT_ABS=0.10 python - <<'PY'
from finam_core.strategy.breakout_reactive import BreakoutReactiveStrategy

s = BreakoutReactiveStrategy(symbol="BRM6@RTSX")

assert s.on_quote({"symbol": "BRM6@RTSX", "last": 100.00}) is None
assert s.on_quote({"symbol": "BRM6@RTSX", "last": 100.05}) is None
assert s.on_quote({"symbol": "BRM6@RTSX", "last": 100.10}) is None

sig = s.on_quote({"symbol": "BRM6@RTSX", "last": 100.25})
assert sig is not None
assert sig["side"] == "BUY"
assert sig["reason"] == "breakout_up"
assert sig["score"] > 1.0

s2 = BreakoutReactiveStrategy(symbol="BRM6@RTSX")
s2.on_quote({"symbol": "BRM6@RTSX", "last": 100.00})
s2.on_quote({"symbol": "BRM6@RTSX", "last": 99.95})
s2.on_quote({"symbol": "BRM6@RTSX", "last": 99.90})

sig2 = s2.on_quote({"symbol": "BRM6@RTSX", "last": 99.75})
assert sig2 is not None
assert sig2["side"] == "SELL"
assert sig2["reason"] == "breakout_down"
assert sig2["score"] > 1.0

print("OK breakout_reactive_score")
PY
