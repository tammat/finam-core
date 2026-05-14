#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/partial_close_engine.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PartialCloseEngine" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_PARTIAL_CLOSE_DECISION" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_PARTIAL_CLOSE_ENGINE" src/finam_core/pipelines/paper_pipeline.py

echo "OK: partial close pipeline compile"
