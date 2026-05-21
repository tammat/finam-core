#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/portfolio_governance_advisor.py \
  src/finam_core/runtime/portfolio_governance_repository.py \
  src/scripts/build_portfolio_governance_event.py

echo "TEST_PORTFOLIO_GOVERNANCE_REPOSITORY_COMPILE_OK"
