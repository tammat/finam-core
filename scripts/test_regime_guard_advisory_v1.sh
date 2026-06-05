#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/regime_guard_candidate_reader.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_REGIME_GUARD_ADVISORY" src/finam_core/pipelines/paper_pipeline.py
grep -q "actual_block=0" src/finam_core/pipelines/paper_pipeline.py
grep -q "advisory_only=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "regime_guard_advisory_v1" src/finam_core/pipelines/paper_pipeline.py

echo REGIME_GUARD_ADVISORY_V1_OK
