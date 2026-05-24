#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/runtime/apply_regime_matrix_runtime_modifier.py

grep -q "apply_context_runtime_filter.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_regime_matrix_runtime_modifier.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_active_contract_lifecycle_filter.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

ctx_pos = text.find("apply_context_runtime_filter.py")
matrix_pos = text.find("apply_regime_matrix_runtime_modifier.py")
life_pos = text.find("apply_active_contract_lifecycle_filter.py")

assert ctx_pos != -1
assert matrix_pos != -1
assert life_pos != -1
assert ctx_pos < matrix_pos < life_pos

print("REGIME_MATRIX_MODIFIER_AFTER_CONTEXT_BEFORE_LIFECYCLE_OK")
PY

echo "RESEARCH_PIPELINE_REGIME_MATRIX_RUNTIME_MODIFIER_WIRING_OK"
