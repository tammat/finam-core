#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/guard_shadow_accumulator.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "GuardShadowAccumulator" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_GUARD_SHADOW_ACCUMULATION_RECORDED" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_GUARD_SHADOW_ACCUMULATION_FAILED" src/finam_core/pipelines/paper_pipeline.py
grep -q "guard_shadow_accumulation_v1" src/finam_core/pipelines/paper_pipeline.py

echo GUARD_SHADOW_ACCUMULATION_PIPELINE_V1_OK
