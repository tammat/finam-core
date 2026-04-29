#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src SIGNAL_MIN_CONFIDENCE=0.5 SIGNAL_SCORE_MIN=0 SIGNAL_SCORE_MAX=100 python - <<'PY'
from finam_core.signals.signal_intent import SignalIntent
from finam_core.signals.signal_router import SignalRouter

r = SignalRouter()

ok = r.route({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "score": 80, "reason": "breakout"})
assert ok.allowed is True
assert round(ok.intent.confidence, 4) == 0.8

dup = r.route({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "score": 80, "reason": "breakout"})
assert dup.allowed is False
assert dup.reason == "duplicate_signal"

low = r.route({"symbol": "BRM6@RTSX", "side": "SELL", "qty": 1, "score": 10})
assert low.allowed is False
assert low.reason == "low_confidence"

bad = r.route({"symbol": "BRM6@RTSX", "side": "HOLD", "qty": 1, "score": 90})
assert bad.allowed is False
assert bad.reason == "invalid_side"

direct = r.route(SignalIntent("SBER@MISX", "BUY", 1, "test", confidence=0.9))
assert direct.allowed is True
assert direct.intent.confidence == 0.9

print("OK signal_router")
PY
