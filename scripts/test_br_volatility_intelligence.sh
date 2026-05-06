#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.strategy.br_volatility_intelligence import BRVolatilityIntelligence

v = BRVolatilityIntelligence()

d = v.evaluate(atr_short=0.5, atr_long=1.0, price=110.0)
assert d.volatility_regime == "compression"
assert d.size_multiplier == 0.5

d = v.evaluate(atr_short=1.5, atr_long=1.0, price=110.0)
assert d.volatility_regime == "expansion"
assert d.confirmation_ticks == 2

d = v.evaluate(atr_short=0.05, atr_long=1.0, price=110.0)
assert d.volatility_regime == "dead_market"
assert d.size_multiplier == 0.0

d = v.evaluate(atr_short=5.0, atr_long=1.0, price=110.0)
assert d.volatility_regime == "panic_vol"
assert d.size_multiplier == 0.25

print("BR_VOLATILITY_INTELLIGENCE_OK")
PY
