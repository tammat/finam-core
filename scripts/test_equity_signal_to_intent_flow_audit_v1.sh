#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY SIGNAL TO INTENT FLOW AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_signal_to_intent_flow_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_signal_to_intent_flow_audit_v1.py \
  | tee /tmp/equity_signal_to_intent_flow_audit_v1.log

grep -q "EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_V1_OK" /tmp/equity_signal_to_intent_flow_audit_v1.log
grep -q "EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_SUMMARY" /tmp/equity_signal_to_intent_flow_audit_v1.log
grep -q "signals_total=" /tmp/equity_signal_to_intent_flow_audit_v1.log
grep -q "execution_intents_total=" /tmp/equity_signal_to_intent_flow_audit_v1.log
grep -q "VERDICT=" /tmp/equity_signal_to_intent_flow_audit_v1.log
grep -q "db_update=0" /tmp/equity_signal_to_intent_flow_audit_v1.log

echo
echo "=== EQUITY SIGNAL TO INTENT FLOW SUMMARY ==="
grep -E "EQUITY_FLOW_RUNTIME_ROW|EQUITY_FLOW_BAR_ROW|EQUITY_FLOW_SIGNAL_ROW|EQUITY_FLOW_INTENT_ROW|EQUITY_FLOW_TRADE_ROW|signals_total=|execution_intents_total=|trades_total=|clean_trades_total=|VERDICT=" \
  /tmp/equity_signal_to_intent_flow_audit_v1.log | head -160

echo TEST_EQUITY_SIGNAL_TO_INTENT_FLOW_AUDIT_V1_OK
