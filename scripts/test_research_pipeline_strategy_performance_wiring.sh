#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/research/build_strategy_performance.py \
  src/finam_core/research/strategy_performance_repository.py

grep -q "build_strategy_regime_performance.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_performance.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_regime_matrix.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

regime_perf = text.find("build_strategy_regime_performance.py")
strategy_perf = text.find("build_strategy_performance.py")
regime_matrix = text.find("build_strategy_regime_matrix.py")

assert regime_perf != -1
assert strategy_perf != -1
assert regime_matrix != -1
assert regime_perf < strategy_perf < regime_matrix

print("STRATEGY_PERFORMANCE_AFTER_REGIME_PERFORMANCE_BEFORE_MATRIX_OK")
PY

echo "RESEARCH_PIPELINE_STRATEGY_PERFORMANCE_WIRING_OK"
