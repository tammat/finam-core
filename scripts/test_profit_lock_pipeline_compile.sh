#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/profit_lock_engine.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "ProfitLockEngine" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_PROFIT_LOCK_DECISION" src/finam_core/pipelines/paper_pipeline.py
grep -q "ENABLE_PROFIT_LOCK_ENGINE" src/finam_core/pipelines/paper_pipeline.py

echo "OK: profit lock pipeline compile"
