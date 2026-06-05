#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/runtime_guard_reader.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_RUNTIME_GUARD_ADVISORY" src/finam_core/pipelines/paper_pipeline.py
grep -q "advisory_only=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_runtime_guard_advisory_v1" src/finam_core/pipelines/paper_pipeline.py
grep -q "symbol=str(sym)" src/finam_core/pipelines/paper_pipeline.py

echo RUNTIME_GUARD_ADVISORY_V1_OK
