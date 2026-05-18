#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/statistical_validation_decision.py \
  src/finam_core/analytics/statistical_validation_engine.py

python - <<'PY'
from finam_core.analytics.statistical_validation_decision import StatisticalValidationDecisionEngine
from finam_core.analytics.statistical_validation_engine import StatisticalValidationResult

engine = StatisticalValidationDecisionEngine()

small = StatisticalValidationResult(4, 1, 0.25, 0.5, 0.25, -0.1, 0.4, 0.9)
assert engine.decide(small).decision == "INSUFFICIENT_DATA"

reject = StatisticalValidationResult(40, -1, -0.025, 0.4, -0.02, -0.1, 0.05, 0.6)
assert engine.decide(reject).decision == "REJECT"

watch = StatisticalValidationResult(40, 1, 0.025, 0.5, 0.02, -0.01, 0.08, 0.75)
assert engine.decide(watch).decision == "WATCH"

strong = StatisticalValidationResult(100, 20, 0.2, 0.7, 0.2, 0.05, 0.35, 0.97)
assert engine.decide(strong).decision == "ACCEPT_STRONG"

weak = StatisticalValidationResult(100, 8, 0.08, 0.6, 0.08, 0.01, 0.15, 0.88)
assert engine.decide(weak).decision == "ACCEPT_WEAK"

print("OK: statistical validation decision")
PY
