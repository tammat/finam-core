#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY VOLATILITY GATE CALLSITE AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_volatility_gate_callsite_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_volatility_gate_callsite_audit_v1.py \
  | tee /tmp/equity_volatility_gate_callsite_audit_v1.log

grep -q "EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_V1_OK" /tmp/equity_volatility_gate_callsite_audit_v1.log
grep -q "EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_SUMMARY" /tmp/equity_volatility_gate_callsite_audit_v1.log
grep -q "br_gate_hits=" /tmp/equity_volatility_gate_callsite_audit_v1.log
grep -q "equity_hits=" /tmp/equity_volatility_gate_callsite_audit_v1.log
grep -q "VERDICT=" /tmp/equity_volatility_gate_callsite_audit_v1.log
grep -q "db_update=0" /tmp/equity_volatility_gate_callsite_audit_v1.log

echo
echo "=== EQUITY VOLATILITY GATE CALLSITE SUMMARY ==="
grep -E "EQUITY_VOL_GATE_CALLSITE_HIT|EQUITY_VOL_GATE_CALLSITE_CONTEXT|files_with_hits=|hits_total=|br_gate_hits=|equity_hits=|audit_writer_hits=|VERDICT=" \
  /tmp/equity_volatility_gate_callsite_audit_v1.log | head -220

echo TEST_EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_V1_OK
