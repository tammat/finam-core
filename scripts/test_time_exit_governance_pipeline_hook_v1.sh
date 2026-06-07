#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/time_exit_governance_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "time_exit_governance_pipeline_hook_v1_call" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_TIME_EXIT_GOVERNANCE_V1" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "TimeExitGovernanceV1" \
  src/finam_core/pipelines/paper_pipeline.py

echo TEST_TIME_EXIT_GOVERNANCE_PIPELINE_HOOK_V1_OK
