#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY SIGNAL GATE DIAGNOSTIC V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_signal_gate_diagnostic_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_signal_gate_diagnostic_v1.py \
  | tee /tmp/equity_signal_gate_diagnostic_v1.log

grep -q "EQUITY_SIGNAL_GATE_DIAGNOSTIC_V1_OK" /tmp/equity_signal_gate_diagnostic_v1.log
grep -q "EQUITY_SIGNAL_GATE_ROWS" /tmp/equity_signal_gate_diagnostic_v1.log
grep -q "EQUITY_SIGNAL_GATE_DIAGNOSTIC_SUMMARY" /tmp/equity_signal_gate_diagnostic_v1.log
grep -q "db_update=0" /tmp/equity_signal_gate_diagnostic_v1.log
grep -q "VERDICT=" /tmp/equity_signal_gate_diagnostic_v1.log

echo
echo "=== EQUITY SIGNAL GATE SUMMARY ==="
grep -E "EQUITY_SIGNAL_GATE_ROW|runtime_equity_rows=|enabled_equities=|equities_with_bars=|equities_with_trades=|equities_enabled_with_bars_no_trades=|VERDICT=" \
  /tmp/equity_signal_gate_diagnostic_v1.log

echo TEST_EQUITY_SIGNAL_GATE_DIAGNOSTIC_V1_OK
