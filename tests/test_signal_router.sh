#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src SIGNAL_MIN_CONFIDENCE=0.5 python - <<'PY'
from finam_core.signals.signal_intent import SignalIntent
from finam_core.signals.signal_router import SignalRouter

r = SignalRouter()

ok = r.route(SignalIntent("BRM6@RTSX", "BUY", 1, "test", confidence=0.8, reason="breakout"))
assert ok.allowed is True
assert ok.intent.to_dict()["side"] == "BUY"

dup = r.route(SignalIntent("BRM6@RTSX", "BUY", 1, "test", confidence=0.8, reason="breakout"))
assert dup.allowed is False
assert dup.reason == "duplicate_signal"

low = r.route(SignalIntent("BRM6@RTSX", "SELL", 1, "test", confidence=0.1))
assert low.allowed is False
assert low.reason == "low_confidence"

bad = r.route({"symbol": "BRM6@RTSX", "side": "HOLD", "qty": 1})
assert bad.allowed is False
assert bad.reason == "invalid_side"

print("OK signal_router")
PY
