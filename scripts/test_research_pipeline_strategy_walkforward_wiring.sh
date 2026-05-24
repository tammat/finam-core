#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/research/build_strategy_walkforward.py \
  src/finam_core/research/walkforward_repository.py

grep -q "build_strategy_performance.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_walkforward.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_regime_matrix.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

strategy_perf = text.find("build_strategy_performance.py")
walkforward = text.find("build_strategy_walkforward.py")
regime_matrix = text.find("build_strategy_regime_matrix.py")

assert strategy_perf != -1
assert walkforward != -1
assert regime_matrix != -1
assert strategy_perf < walkforward < regime_matrix

print("STRATEGY_WALKFORWARD_AFTER_PERFORMANCE_BEFORE_MATRIX_OK")
PY

echo "RESEARCH_PIPELINE_STRATEGY_WALKFORWARD_WIRING_OK"
