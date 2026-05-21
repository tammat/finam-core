#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/exit_policy_advisor.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "EXIT_POLICY_ADVISORY_APPLIED" src/finam_core/pipelines/paper_pipeline.py
grep -q "log_exit_policy_advisory" src/finam_core/pipelines/paper_pipeline.py
grep -q "br_conservative_breakout" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_EXIT_POLICY_ADVISORY_PIPELINE_COMPILE_OK"
