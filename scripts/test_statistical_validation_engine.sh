#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/statistical_validation_engine.py

python - <<'PY'
from finam_core.analytics.statistical_validation_engine import StatisticalValidationEngine

engine = StatisticalValidationEngine()

result = engine.validate([1.0, 2.0, -0.5, 0.5], bootstrap_samples=500, seed=1)

assert result.trades == 4
assert round(result.net_pnl, 4) == 3.0
assert round(result.expectancy, 4) == 0.75
assert result.winrate == 0.75
assert result.expectancy_ci_low <= result.bootstrap_mean_expectancy <= result.expectancy_ci_high
assert 0.0 <= result.probability_positive_expectancy <= 1.0

empty = engine.validate([])
assert empty.trades == 0
assert empty.probability_positive_expectancy == 0.0

print("OK: statistical validation engine")
PY
