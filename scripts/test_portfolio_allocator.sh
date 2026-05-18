#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/portfolio/portfolio_allocator.py

python - <<'PY'
from finam_core.portfolio.portfolio_allocator import (
    PortfolioAllocator,
    StrategyAllocationInput,
)

allocator = PortfolioAllocator()

items = [
    StrategyAllocationInput("S1", "BRM6@RTSX", "A+", 60, 0.98, -1.0),
    StrategyAllocationInput("S2", "SBER@MISX", "A", 50, 0.94, -1.5),
    StrategyAllocationInput("S3", "GAZP@MISX", "B", 35, 0.88, -2.0),
    StrategyAllocationInput("S4", "USDRUBF@RTSX", "D", 5, 0.55, -1.0),
]

result = allocator.allocate(items)

assert len(result) == 4
assert result[0].decision == "РАСПРЕДЕЛИТЬ"
assert result[0].capital_weight <= 0.35
assert result[3].capital_weight == 0.0
assert result[3].decision == "НЕ_РАСПРЕДЕЛЯТЬ"

empty = allocator.allocate([
    StrategyAllocationInput("BAD", "TEST", "D", 0, 0.1, -1.0),
])
assert empty[0].capital_weight == 0.0
assert empty[0].reason == "нет_допустимых_стратегий"

print("OK: portfolio allocator")
PY
