#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/runtime/regime_runtime_override_repository.py \
  src/finam_core/risk/runtime_override_gate.py

grep -q "RuntimeRegimeOverrideRepository" src/finam_core/pipelines/paper_pipeline.py
grep -q "apply_runtime_override_gate" src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_override_gate_allows_paper_signal" src/finam_core/pipelines/paper_pipeline.py
grep -q "RUNTIME_OVERRIDE_GATE_BLOCK" src/finam_core/pipelines/paper_pipeline.py
grep -q "RUNTIME_OVERRIDE_GATE_ADJUST" src/finam_core/pipelines/paper_pipeline.py

echo "PAPER_PIPELINE_RUNTIME_OVERRIDE_GATE_WIRING_OK"
