#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/portfolio_governance_advisor.py

echo "TEST_PORTFOLIO_GOVERNANCE_ADVISOR_COMPILE_OK"
