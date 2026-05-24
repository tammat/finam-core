#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/context_runtime_filter.py \
  src/scripts/runtime/apply_context_runtime_filter.py

python - <<'PY'
from finam_core.runtime.context_runtime_filter import build_context_runtime_decision

assert build_context_runtime_decision(
    context_status="WATCH_CONTEXT", trades=82, profit_factor=1.15, expectancy=0.47
).score_multiplier > 1

assert build_context_runtime_decision(
    context_status="BAD_CONTEXT", trades=13, profit_factor=0.76, expectancy=-0.41
).score_multiplier < 1

assert build_context_runtime_decision(
    context_status="LOW_SAMPLE", trades=3, profit_factor=2.0, expectancy=1.0
).suffix == "CTX_LOW_SAMPLE"

print("CONTEXT_RUNTIME_FILTER_UNIT_OK")
PY

grep -q "strategy_regime_performance" src/scripts/runtime/apply_context_runtime_filter.py
grep -q "feature_snapshots" src/scripts/runtime/apply_context_runtime_filter.py
grep -q "CONTEXT_RUNTIME_FILTER_OK" src/scripts/runtime/apply_context_runtime_filter.py

echo "CONTEXT_RUNTIME_FILTER_V1_TEST_OK"
