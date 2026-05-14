#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/pipeline_kernel.py \
  src/finam_core/pipelines/pipeline_orchestrator.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class PipelineKernel" src/finam_core/pipelines/pipeline_kernel.py
grep -q "PipelineKernelInput" src/finam_core/pipelines/pipeline_orchestrator.py
grep -q "kernel.process_quote" src/finam_core/pipelines/pipeline_orchestrator.py

echo "OK: pipeline kernel compile"
