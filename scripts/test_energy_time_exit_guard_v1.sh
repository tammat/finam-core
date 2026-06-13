#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_ENERGY_TIME_EXIT_GUARD_V1_START"

python3 -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -R "PIPE_ENERGY_TIME_EXIT_GUARD" \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/exit_lifecycle_manager.py

grep -R "ENERGY_TIME_EXIT_MIN_HOLD_SEC" \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/execution/exit_lifecycle_manager.py

echo "TEST_ENERGY_TIME_EXIT_GUARD_V1_OK"
