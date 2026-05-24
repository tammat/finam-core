#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/build_portfolio_risk_state.py \
  src/finam_core/risk/portfolio_risk_gate.py

grep -q "portfolio_risk_state" \
  src/scripts/build_portfolio_risk_state.py

grep -q "PortfolioRiskDecision" \
  src/finam_core/risk/portfolio_risk_gate.py

echo "TEST_PORTFOLIO_RISK_V3_OK"
