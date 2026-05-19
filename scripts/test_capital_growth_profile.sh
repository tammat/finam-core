#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_profile.py \
  src/finam_core/runtime/capital_growth_mode.py

python - <<'PY'
import os

from finam_core.runtime.capital_growth_profile import CapitalGrowthProfile
from finam_core.runtime.capital_growth_mode import CapitalGrowthMode

p = CapitalGrowthProfile()

assert p.load("conservative").risk_a == 0.006
assert p.load("growth").risk_a == 0.012
assert p.load("aggressive").risk_a == 0.015

os.environ["CAPITAL_GROWTH_PROFILE"] = "aggressive"

m = CapitalGrowthMode()

a = m.decide(
    trade_quality_grade="A",
    trade_quality_score=82,
    expected_value=100,
    probability_tp=0.58,
    probability_sl=0.35,
    risk_reward=2.0,
    portfolio_heat=0.2,
    runtime_severity="INFO",
)

assert a.allowed is True
assert abs(a.risk_pct - 0.015) < 0.0001

b = m.decide(
    trade_quality_grade="B",
    trade_quality_score=70,
    expected_value=100,
    probability_tp=0.58,
    probability_sl=0.35,
    risk_reward=2.0,
    portfolio_heat=0.2,
    runtime_severity="INFO",
)

assert b.allowed is False

print("OK: capital growth profile")
PY
