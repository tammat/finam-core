#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/adaptive_portfolio_allocator.py \
  src/scripts/run_adaptive_portfolio_allocator.py

python - <<'PY'
from finam_core.runtime.adaptive_portfolio_allocator import (
    AdaptivePortfolioAllocator,
)

a = AdaptivePortfolioAllocator()

r = a.allocate(
    symbol="MGNT@MISX",
    entry_price=2445,

    quality_score=82,
    quality_grade="A",

    expected_value=176,

    available_capital=300000,
    portfolio_heat=0.2,

    correlation_pressure=0,
    existing_position=False,
)

assert r.allowed is True
assert r.allocated_qty > 0

blocked = a.allocate(
    symbol="LKOH@MISX",
    entry_price=5000,

    quality_score=80,
    quality_grade="A",

    expected_value=200,

    available_capital=300000,
    portfolio_heat=0.2,

    correlation_pressure=2,
    existing_position=False,
)

assert blocked.allowed is False

print("OK: adaptive portfolio allocator")
PY
