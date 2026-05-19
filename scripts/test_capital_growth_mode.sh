#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_mode.py \
  src/scripts/run_capital_growth_mode.py

python - <<'PY'
from finam_core.runtime.capital_growth_mode import CapitalGrowthMode

m = CapitalGrowthMode()

a = m.decide(
    trade_quality_grade="A",
    trade_quality_score=80,
    expected_value=100,
    probability_tp=0.58,
    probability_sl=0.35,
    risk_reward=2.0,
    portfolio_heat=0.2,
    runtime_severity="INFO",
)

assert a.allowed is True
assert abs(a.risk_pct - 0.012) < 0.0001

b = m.decide(
    trade_quality_grade="C",
    trade_quality_score=48,
    expected_value=100,
    probability_tp=0.55,
    probability_sl=0.40,
    risk_reward=2.0,
    portfolio_heat=0.2,
    runtime_severity="INFO",
)

assert b.allowed is False

blocked = m.decide(
    trade_quality_grade="A",
    trade_quality_score=80,
    expected_value=100,
    probability_tp=0.58,
    probability_sl=0.35,
    risk_reward=2.0,
    portfolio_heat=0.8,
    runtime_severity="INFO",
)

assert blocked.allowed is False

print("OK: capital growth mode")
PY
