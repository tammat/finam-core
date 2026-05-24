#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/research/build_strategy_research_verdict.py \
  src/finam_core/research/research_verdict_repository.py

grep -q "build_strategy_walkforward.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_research_verdict.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_strategy_regime_matrix.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

walkforward = text.find("build_strategy_walkforward.py")
verdict = text.find("build_strategy_research_verdict.py")
regime_matrix = text.find("build_strategy_regime_matrix.py")

assert walkforward != -1
assert verdict != -1
assert regime_matrix != -1
assert walkforward < verdict < regime_matrix

print("STRATEGY_RESEARCH_VERDICT_AFTER_WALKFORWARD_BEFORE_MATRIX_OK")
PY

echo "RESEARCH_PIPELINE_STRATEGY_RESEARCH_VERDICT_WIRING_OK"
