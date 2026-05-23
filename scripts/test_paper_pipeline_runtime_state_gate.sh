#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_state_gate.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RuntimeStateGate" src/finam_core/pipelines/paper_pipeline.py
grep -q "gate=runtime_state" src/finam_core/pipelines/paper_pipeline.py
grep -q "NG_CONSERVATIVE_BREAKOUT_M1" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PAPER_PIPELINE_RUNTIME_STATE_GATE_OK"
