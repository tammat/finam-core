#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/trade_exit_policy_repository.py \
  src/scripts/build_trade_exit_policy_context.py

grep -q "trade_exit_policy_context" src/finam_core/analytics/trade_exit_policy_repository.py
grep -q "portfolio_governance_events" src/finam_core/analytics/trade_exit_policy_repository.py
grep -q "TRADE_EXIT_POLICY_CONTEXT_SUMMARY" src/scripts/build_trade_exit_policy_context.py

echo "TEST_TRADE_EXIT_POLICY_CONTEXT_OK"
