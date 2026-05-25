#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/scripts/replay_br_pipeline.py

grep -q "REPLAY_DISABLE_RUNTIME_CONTROL" src/finam_core/pipelines/paper_pipeline.py

echo "REPLAY_RUNTIME_CONTROL_BYPASS_TEST_OK"
