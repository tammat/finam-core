#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/signals/signal_intent.py

python - <<'PY'
from finam_core.signals.signal_intent import SignalIntent

intent = SignalIntent(
    symbol="BRM6@RTSX",
    side="buy",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    qty=1,
    entry_price=108.5,
    stop_price=108.0,
    take_profit=109.5,
    confidence=0.75,
)

assert intent.side == "BUY"
assert intent.intent_type == "ENTRY"
assert intent.continuous_symbol == "BR_CONT"
assert intent.signal_id.startswith("sig-BR_CONSERVATIVE_BREAKOUT-BRM6@RTSX-")

d = intent.to_dict()

assert d["symbol"] == "BRM6@RTSX"
assert d["continuous_symbol"] == "BR_CONT"
assert d["price"] == 108.5
assert d["features"]["entry"] == 108.5
assert d["features"]["stop"] == 108.0
assert d["features"]["take"] == 109.5
assert d["features"]["strategy"] == "BR_CONSERVATIVE_BREAKOUT"

legacy = SignalIntent.from_dict({
    "symbol": "PLZL@MISX",
    "side": "SELL",
    "qty": 1,
    "price": 2135.0,
    "strategy": "TREND_PULLBACK_EQUITY",
    "features": {
        "stop": 2145.0,
        "take": 2110.0,
    }
})

assert legacy.symbol == "PLZL@MISX"
assert legacy.continuous_symbol == "PLZL@MISX"
assert legacy.entry_price == 2135.0
assert legacy.stop_price == 2145.0
assert legacy.take_profit == 2110.0

print("OK: SignalIntent v2 canonical contract works")
PY
