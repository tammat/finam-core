#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.risk.volatility_risk import VolatilityRiskEngine

e = VolatilityRiskEngine()
p = e.compute(atr=0.2)

assert round(p.stop_abs, 6) == round(0.2 * e.stop_atr_mult, 6)
assert round(p.take_abs, 6) == round(0.2 * e.take_atr_mult, 6)
assert p.qty >= e.min_qty
assert p.qty <= e.max_qty
assert p.risk_amount == p.qty * p.stop_abs

p2 = e.compute(atr=0)
assert p2.atr == e.default_atr

print("OK volatility_risk")
PY
