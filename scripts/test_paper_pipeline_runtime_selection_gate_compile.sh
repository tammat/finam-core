#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/runtime_selection_gate.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RuntimeSelectionGate" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_M1_SELECTION_REJECTED" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_NG_M1_SELECTION_ACCEPTED" src/finam_core/pipelines/paper_pipeline.py

echo "PAPER_PIPELINE_RUNTIME_SELECTION_GATE_COMPILE_OK"
