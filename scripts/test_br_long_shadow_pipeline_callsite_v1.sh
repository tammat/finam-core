#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "br_long_shadow_pipeline_hook_v1_call" src/finam_core/pipelines/paper_pipeline.py
grep -q "BR_LONG_SHADOW_BLOCK" src/finam_core/pipelines/paper_pipeline.py
grep -q "_br_long_shadow_pipeline_hook_v1(" src/finam_core/pipelines/paper_pipeline.py

echo BR_LONG_SHADOW_PIPELINE_CALLSITE_V1_OK
