#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY ON BAR FLOW AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_strategy_on_bar_flow_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_strategy_on_bar_flow_audit_v1.py \
  | tee /tmp/equity_strategy_on_bar_flow_audit_v1.log

grep -q "EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_V1_OK" /tmp/equity_strategy_on_bar_flow_audit_v1.log
grep -q "EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_SUMMARY" /tmp/equity_strategy_on_bar_flow_audit_v1.log
grep -q "strategy_by_symbol_hits=" /tmp/equity_strategy_on_bar_flow_audit_v1.log
grep -q "on_bar_hits=" /tmp/equity_strategy_on_bar_flow_audit_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_on_bar_flow_audit_v1.log
grep -q "db_update=0" /tmp/equity_strategy_on_bar_flow_audit_v1.log

echo
echo "=== EQUITY STRATEGY ON BAR FLOW SUMMARY ==="
grep -E "EQUITY_ON_BAR_FLOW_CODE_HIT|EQUITY_ON_BAR_FLOW_CODE_CONTEXT|strategy_by_symbol_hits=|on_bar_hits=|equity_route_hits=|guard_hits=|runtime_strategy_hits=|VERDICT=" \
  /tmp/equity_strategy_on_bar_flow_audit_v1.log | head -260

echo TEST_EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_V1_OK
