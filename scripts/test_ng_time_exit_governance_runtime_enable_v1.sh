#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/time_exit_governance_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "ng_time_exit_governance_runtime_enable_v1_call" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_NG_TIME_EXIT_GOVERNANCE_BLOCK_V1" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "ENABLE_NG_TIME_EXIT_GOVERNANCE_V1" \
  src/finam_core/pipelines/paper_pipeline.py

echo TEST_NG_TIME_EXIT_GOVERNANCE_RUNTIME_ENABLE_V1_OK
