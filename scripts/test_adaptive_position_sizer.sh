#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/risk/adaptive_position_sizer.py

python - <<'PY'
from finam_core.risk.adaptive_position_sizer import AdaptivePositionSizer

sizer = AdaptivePositionSizer()

normal = sizer.size(
    base_qty=10,
    confidence=0.60,
    institutional_flow_regime="NORMAL_FLOW",
    volatility_quality=0.50,
    portfolio_heat=0.0,
)

assert normal.final_qty == 10.0
assert normal.multiplier == 1.0

trend = sizer.size(
    base_qty=10,
    confidence=0.88,
    institutional_flow_regime="TREND_INITIATION",
    institutional_flow_bias="MOMENTUM_BIAS",
    smart_money_score=0.75,
    volatility_quality=0.85,
    portfolio_heat=0.0,
)

assert trend.final_qty > normal.final_qty
assert trend.multiplier <= 1.5

trap = sizer.size(
    base_qty=10,
    confidence=0.60,
    institutional_flow_regime="BREAKOUT_TRAP",
    institutional_flow_bias="FADE_BIAS",
    smart_money_score=0.60,
    volatility_quality=0.50,
    portfolio_heat=0.0,
)

assert trap.final_qty < normal.final_qty

hot = sizer.size(
    base_qty=10,
    confidence=0.88,
    institutional_flow_regime="TREND_INITIATION",
    smart_money_score=0.75,
    volatility_quality=0.85,
    portfolio_heat=0.90,
)

assert hot.final_qty < trend.final_qty
assert hot.heat_multiplier == 0.25

print("OK: AdaptivePositionSizer")
PY
