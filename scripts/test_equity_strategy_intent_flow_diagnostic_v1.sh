#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY INTENT FLOW DIAGNOSTIC V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_intent_flow_diagnostic_v1.py

EQUITY_INTENT_SYMBOL="${EQUITY_INTENT_SYMBOL:-SBER@MISX}" \
PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_intent_flow_diagnostic_v1.py \
  | tee /tmp/equity_strategy_intent_flow_diagnostic_v1.log

grep -q "EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_V1_OK" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "EQUITY_INTENT_RUNTIME_ROWS" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "EQUITY_INTENT_MARKET_BARS" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "EQUITY_INTENT_FEATURE_PROXY" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_SUMMARY" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "db_update=0" /tmp/equity_strategy_intent_flow_diagnostic_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_intent_flow_diagnostic_v1.log

echo
echo "=== EQUITY STRATEGY INTENT FLOW SUMMARY ==="
grep -E "EQUITY_INTENT_RUNTIME_ROW|EQUITY_INTENT_MARKET_BARS_ROW|EQUITY_INTENT_FEATURE_PROXY|bar_status=|required_bars=|trades_count=|diagnosis=|next_step=|VERDICT=" \
  /tmp/equity_strategy_intent_flow_diagnostic_v1.log

echo TEST_EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_V1_OK
