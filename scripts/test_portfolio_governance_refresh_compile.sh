#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/portfolio_governance_refresh.py \
  src/scripts/build_portfolio_heat.py \
  src/scripts/build_portfolio_governance_event.py

echo "TEST_PORTFOLIO_GOVERNANCE_REFRESH_COMPILE_OK"
