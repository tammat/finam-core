#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/quote_normalizer.py \
  src/finam_core/pipelines/pipeline_orchestrator.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "QuoteNormalizer.normalize" src/finam_core/pipelines/pipeline_orchestrator.py
grep -q "NormalizedQuote" src/finam_core/pipelines/quote_normalizer.py
grep -q "QuoteEventContext" src/finam_core/pipelines/pipeline_orchestrator.py

echo "OK: quote normalizer orchestrator compile"
