#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/pipeline_orchestrator.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class PipelineOrchestrator" src/finam_core/pipelines/pipeline_orchestrator.py
grep -q "QuoteEventContext" src/finam_core/pipelines/paper_pipeline.py
grep -q "def _on_quote_impl" src/finam_core/pipelines/paper_pipeline.py
grep -q "pipeline_orchestrator.on_quote" src/finam_core/pipelines/paper_pipeline.py

echo "OK: pipeline orchestrator compile"
