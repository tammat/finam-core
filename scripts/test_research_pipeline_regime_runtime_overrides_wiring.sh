#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/runtime/build_regime_runtime_overrides.py

grep -q "apply_regime_matrix_runtime_modifier.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_regime_runtime_overrides.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_active_contract_lifecycle_filter.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

matrix_pos = text.find("apply_regime_matrix_runtime_modifier.py")
override_pos = text.find("build_regime_runtime_overrides.py")
life_pos = text.find("apply_active_contract_lifecycle_filter.py")

assert matrix_pos != -1
assert override_pos != -1
assert life_pos != -1
assert matrix_pos < override_pos < life_pos

print("REGIME_RUNTIME_OVERRIDES_AFTER_MATRIX_BEFORE_LIFECYCLE_OK")
PY

echo "RESEARCH_PIPELINE_REGIME_RUNTIME_OVERRIDES_WIRING_OK"
