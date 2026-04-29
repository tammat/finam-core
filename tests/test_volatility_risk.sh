#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src VOL_RISK_PER_TRADE=100 VOL_RISK_MIN_QTY=1 VOL_RISK_MAX_QTY=1000 VOL_RISK_MIN_CONFIDENCE_FACTOR=0.25 python - <<'PY'
from finam_core.risk.volatility_risk import VolatilityRiskEngine

e = VolatilityRiskEngine()
p = e.compute(atr=0.2)

assert round(p.stop_abs, 6) == round(0.2 * e.stop_atr_mult, 6)
assert round(p.take_abs, 6) == round(0.2 * e.take_atr_mult, 6)
assert p.qty >= e.min_qty
assert p.qty <= e.max_qty

p_full = e.compute(atr=0.2, confidence=1.0)
p_half = e.compute(atr=0.2, confidence=0.5)
p_low = e.compute(atr=0.2, confidence=0.0)

assert p_full.risk_amount > p_half.risk_amount
assert round(p_half.risk_amount, 6) == round(p_full.risk_amount * 0.5, 6)
assert round(p_low.risk_amount, 6) == round(p_full.risk_amount * 0.25, 6)

p2 = e.compute(atr=0)
assert p2.atr == max(e.default_atr, e.min_atr)

print("OK volatility_risk")
PY
