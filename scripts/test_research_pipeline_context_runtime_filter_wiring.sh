#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/research_pipeline_orchestrator.py \
  src/scripts/runtime/apply_context_runtime_filter.py

grep -q "apply_intermarket_selection_modifier.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_context_runtime_filter.py" src/scripts/research_pipeline_orchestrator.py
grep -q "apply_active_contract_lifecycle_filter.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

im_pos = text.find("apply_intermarket_selection_modifier.py")
ctx_pos = text.find("apply_context_runtime_filter.py")
life_pos = text.find("apply_active_contract_lifecycle_filter.py")

assert im_pos != -1
assert ctx_pos != -1
assert life_pos != -1
assert im_pos < ctx_pos < life_pos

print("CONTEXT_RUNTIME_FILTER_AFTER_INTERMARKET_BEFORE_LIFECYCLE_OK")
PY

echo "RESEARCH_PIPELINE_CONTEXT_RUNTIME_FILTER_WIRING_OK"
