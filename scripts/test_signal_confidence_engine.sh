#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/strategy/signal_confidence.py

python - <<'PY'
from finam_core.strategy.signal_confidence import SignalConfidenceEngine

e = SignalConfidenceEngine()

strong = e.evaluate(
    base_score=0.75,
    smart_money_score=0.80,
    regime_alignment=0.80,
    spread_quality=0.90,
    volatility_quality=0.75,
)

assert strong.action == "ACCEPT"
assert strong.institutional_confirmed is True
assert strong.confidence >= 0.70

weak = e.evaluate(
    base_score=0.45,
    smart_money_score=0.10,
    regime_alignment=0.40,
    spread_quality=0.70,
    volatility_quality=0.40,
)

assert weak.action == "REJECT"
assert weak.institutional_confirmed is False

watch = e.evaluate(
    base_score=0.60,
    smart_money_score=0.50,
    regime_alignment=0.55,
    spread_quality=0.80,
    volatility_quality=0.50,
)

assert watch.action in {"WATCH", "ACCEPT"}

print("OK: SignalConfidenceEngine")
PY
