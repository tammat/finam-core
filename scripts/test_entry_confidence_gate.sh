#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/signal_confidence.py \
  src/finam_core/strategy/entry_confidence_gate.py

python - <<'PY'
from finam_core.strategy.entry_confidence_gate import EntryConfidenceGate

gate = EntryConfidenceGate(min_confidence=0.55)

strong_intent = {
    "symbol": "SBER@MISX",
    "side": "BUY",
    "features": {
        "base_score": 0.75,
        "smart_money_score": 0.82,
        "regime_alignment": 0.80,
        "spread_quality": 0.90,
        "volatility_quality": 0.75,
    }
}

strong = gate.evaluate(strong_intent)

assert strong.accepted is True
assert strong.institutional_confirmed is True
assert strong.confidence >= 0.70

weak_intent = {
    "symbol": "GAZP@MISX",
    "side": "BUY",
    "features": {
        "base_score": 0.40,
        "smart_money_score": 0.10,
        "regime_alignment": 0.35,
        "spread_quality": 0.60,
        "volatility_quality": 0.30,
    }
}

weak = gate.evaluate(weak_intent)

assert weak.accepted is False
assert weak.action == "REJECT"

watch_intent = {
    "symbol": "OZON@MISX",
    "side": "BUY",
    "features": {
        "base_score": 0.60,
        "smart_money_score": 0.50,
        "regime_alignment": 0.55,
        "spread_quality": 0.80,
        "volatility_quality": 0.55,
    }
}

watch = gate.evaluate(watch_intent)

assert watch.confidence >= 0.55

print("OK: EntryConfidenceGate")
PY
