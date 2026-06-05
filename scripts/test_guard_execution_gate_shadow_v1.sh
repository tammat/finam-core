#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/guard_candidate_classification_reader.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_GUARD_EXECUTION_GATE_SHADOW" src/finam_core/pipelines/paper_pipeline.py
grep -q "would_block=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "actual_block=0" src/finam_core/pipelines/paper_pipeline.py
grep -q "advisory_only=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "guard_execution_gate_shadow_v1" src/finam_core/pipelines/paper_pipeline.py

echo GUARD_EXECUTION_GATE_SHADOW_V1_OK
