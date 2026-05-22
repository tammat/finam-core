#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/trade_risk_context_repository.py \
  src/scripts/build_trade_risk_context.py

grep -q "trade_risk_context" src/finam_core/analytics/trade_risk_context_repository.py
grep -q "portfolio_governance_events" src/finam_core/analytics/trade_risk_context_repository.py
grep -q "TRADE_RISK_CONTEXT_SUMMARY" src/scripts/build_trade_risk_context.py

echo "TEST_TRADE_RISK_CONTEXT_OK"
