#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/adaptive_capital_allocator_v2.py \
  src/scripts/run_adaptive_capital_allocator_v2.py

python - <<'PY'
from finam_core.runtime.adaptive_capital_allocator_v2 import (
    AdaptiveCapitalAllocatorV2,
)

a = AdaptiveCapitalAllocatorV2()

strong = a.decide(
    trade_quality_score=88,
    expected_value=3.1,
    probability_tp=0.68,
    probability_sl=0.31,
    market_breadth=0.72,
    runtime_stress_level="INFO",
    portfolio_drawdown_pct=0.02,
    correlation_pressure=0.20,
    runtime_regime="trend_up_high_vol",
)

assert strong.allowed is True
assert strong.capital_multiplier > 1.0

weak = a.decide(
    trade_quality_score=60,
    expected_value=0.4,
    probability_tp=0.45,
    probability_sl=0.48,
    market_breadth=0.30,
    runtime_stress_level="CRITICAL",
    portfolio_drawdown_pct=0.12,
    correlation_pressure=0.80,
    runtime_regime="range",
)

assert weak.allowed is False

print("OK: adaptive capital allocator v2")
PY
