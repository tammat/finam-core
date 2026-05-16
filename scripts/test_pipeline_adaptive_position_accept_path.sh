#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/strategy/entry_confidence_gate.py \
  src/finam_core/risk/adaptive_position_sizer.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

confidence = text.find("if not self._entry_confidence_gate_if_enabled(intent, st):")
sizer = text.find("self._adaptive_position_size_if_enabled(intent, st)")
entry = text.find("ENTRY GATE COORDINATOR")

assert confidence != -1, "confidence gate call missing"
assert sizer != -1, "adaptive sizer call missing"
assert entry != -1, "EntryGateCoordinator marker missing"
assert confidence < sizer < entry, "wrong order: confidence -> sizer -> EntryGateCoordinator"

assert "intent[\"qty\"] = decision.final_qty" in text
assert "adaptive_position_final_qty" in text
assert "adaptive_position_multiplier" in text
assert "PIPE_ADAPTIVE_POSITION_SIZE" in text

print("OK: pipeline adaptive sizing ACCEPT path order")
PY

python - <<'PY'
from finam_core.strategy.entry_confidence_gate import EntryConfidenceGate
from finam_core.risk.adaptive_position_sizer import AdaptivePositionSizer

intent = {
    "symbol": "BRM6@RTSX",
    "qty": 1.0,
    "features": {
        "base_score": 0.75,
        "smart_money_score": 0.75,
        "regime_alignment": 0.80,
        "spread_quality": 0.90,
        "volatility_quality": 0.80,
        "institutional_flow_regime": "TREND_INITIATION",
        "institutional_flow_bias": "MOMENTUM_BIAS",
    },
}

gate = EntryConfidenceGate(min_confidence=0.55)
gate_decision = gate.evaluate(intent)

assert gate_decision.accepted is True
intent["features"]["entry_confidence"] = gate_decision.confidence

sizer = AdaptivePositionSizer()
size_decision = sizer.size(
    base_qty=intent["qty"],
    confidence=intent["features"]["entry_confidence"],
    institutional_flow_regime=intent["features"]["institutional_flow_regime"],
    institutional_flow_bias=intent["features"]["institutional_flow_bias"],
    smart_money_score=intent["features"]["smart_money_score"],
    volatility_quality=intent["features"]["volatility_quality"],
    portfolio_heat=0.0,
)

assert size_decision.final_qty > intent["qty"]
assert size_decision.multiplier <= 1.5

print("OK: confidence ACCEPT leads to adaptive position sizing")
PY
