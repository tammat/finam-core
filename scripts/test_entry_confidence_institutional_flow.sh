#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/signal_confidence.py \
  src/finam_core/strategy/entry_confidence_gate.py

python - <<'PY'
from finam_core.strategy.entry_confidence_gate import EntryConfidenceGate

gate = EntryConfidenceGate(min_confidence=0.55)

base_intent = {
    "symbol": "BRM6@RTSX",
    "features": {
        "base_score": 0.55,
        "smart_money_score": 0.30,
        "regime_alignment": 0.55,
        "spread_quality": 0.90,
        "volatility_quality": 0.50,
    },
}

normal = gate.evaluate(base_intent)

trend = gate.evaluate({
    **base_intent,
    "features": {
        **base_intent["features"],
        "institutional_flow_regime": "TREND_INITIATION",
        "institutional_flow_bias": "MOMENTUM_BIAS",
    },
})

trap = gate.evaluate({
    **base_intent,
    "features": {
        **base_intent["features"],
        "institutional_flow_regime": "BREAKOUT_TRAP",
        "institutional_flow_bias": "FADE_BIAS",
    },
})

assert trend.confidence > normal.confidence
assert trap.confidence < normal.confidence
assert "institutional_flow_regime=TREND_INITIATION" in trend.reason
assert "flow_adjustment=0.1" in trend.reason

print("OK: EntryConfidenceGate uses institutional flow regime")
PY
