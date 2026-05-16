#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/orderflow/institutional_flow_regime.py

python - <<'PY'
from finam_core.orderflow.institutional_flow_regime import InstitutionalFlowRegimeEngine

e = InstitutionalFlowRegimeEngine()

acc = e.classify(
    symbol="SBER@MISX",
    smart_money_score=0.72,
    rvol=3.0,
    absorption_score=0.80,
    sweep_reclaim_score=0.10,
    impulse_score=0.30,
    range_pct=0.003,
)

assert acc.regime == "ACCUMULATION"
assert acc.bias == "LONG_BIAS"

trap = e.classify(
    symbol="SBER@MISX",
    smart_money_score=0.60,
    rvol=2.0,
    absorption_score=0.20,
    sweep_reclaim_score=0.75,
    impulse_score=0.30,
    range_pct=0.012,
)

assert trap.regime == "BREAKOUT_TRAP"
assert trap.bias == "FADE_BIAS"

trend = e.classify(
    symbol="BR_CONT",
    smart_money_score=0.55,
    rvol=2.5,
    absorption_score=0.10,
    sweep_reclaim_score=0.10,
    impulse_score=0.80,
    price_velocity=0.006,
    range_pct=0.014,
)

assert trend.regime == "TREND_INITIATION"
assert trend.bias == "MOMENTUM_BIAS"

normal = e.classify(
    symbol="BR_CONT",
    smart_money_score=0.11,
    rvol=1.0,
    absorption_score=0.0,
    sweep_reclaim_score=0.0,
    impulse_score=0.29,
)

assert normal.regime == "NORMAL_FLOW"
assert normal.bias == "NEUTRAL"

print("OK: InstitutionalFlowRegimeEngine")
PY
