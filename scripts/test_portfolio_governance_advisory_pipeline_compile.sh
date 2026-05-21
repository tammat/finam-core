#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/portfolio_governance_advisor.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PORTFOLIO_GOVERNANCE_ADVISORY_APPLIED" src/finam_core/pipelines/paper_pipeline.py
grep -q "log_portfolio_governance_advisory" src/finam_core/pipelines/paper_pipeline.py

echo "TEST_PORTFOLIO_GOVERNANCE_ADVISORY_PIPELINE_COMPILE_OK"
