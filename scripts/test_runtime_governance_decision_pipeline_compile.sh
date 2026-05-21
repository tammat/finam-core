#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_governance_coordinator_v2.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "RUNTIME_GOVERNANCE_DECISION" src/finam_core/pipelines/paper_pipeline.py
grep -q "log_runtime_governance_decision" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_RUNTIME_GOVERNANCE_DECISION_PIPELINE_COMPILE_OK"
