#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_regime_allocator.py \
  src/scripts/run_capital_growth_regime_allocator.py

python - <<'PY'
from finam_core.runtime.capital_growth_regime_allocator import (
    CapitalGrowthRegimeAllocator,
)

a = CapitalGrowthRegimeAllocator()

aggressive = a.decide(
    runtime_regime="trend_up_high_vol",
    portfolio_drawdown_pct=0.02,
    runtime_winrate=0.61,
    runtime_stress_level="INFO",
    market_breadth=0.70,
)

assert aggressive.profile == "aggressive"

conservative = a.decide(
    runtime_regime="trend",
    portfolio_drawdown_pct=0.10,
    runtime_winrate=0.70,
    runtime_stress_level="INFO",
    market_breadth=0.80,
)

assert conservative.profile == "conservative"

growth = a.decide(
    runtime_regime="range",
    portfolio_drawdown_pct=0.03,
    runtime_winrate=0.52,
    runtime_stress_level="INFO",
    market_breadth=0.45,
)

assert growth.profile == "growth"

print("OK: capital growth regime allocator")
PY
