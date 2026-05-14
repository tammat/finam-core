#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/real_protective_lifecycle.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RealProtectiveLifecycleEngine" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_REAL_PROTECTIVE_LIFECYCLE_RESULT" src/finam_core/pipelines/paper_pipeline.py
grep -q "REAL_PROTECTIVE_LIFECYCLE_ENABLED" src/finam_core/execution/real_protective_lifecycle.py

echo "OK: real protective lifecycle pipeline wired"
