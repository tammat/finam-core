#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/strategy_metrics.py \
  src/finam_core/research/research_repository.py \
  src/finam_core/research/research_runner.py

python - <<'PY'
from finam_core.research.strategy_metrics import calculate_strategy_metrics
from finam_core.research.research_runner import classify_strategy

m = calculate_strategy_metrics([100, -30, 80, -20, 50, 40, -10, 70, -25, 60] * 3)

decision, reason = classify_strategy(m)

assert m.trades == 30
assert m.expectancy > 0
assert m.profit_factor > 1.1
assert decision == "ACCEPT"

print("RESEARCH_LAYER_V1_TEST_OK")
PY
