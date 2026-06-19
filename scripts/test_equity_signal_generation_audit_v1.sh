#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY SIGNAL GENERATION AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_signal_generation_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_signal_generation_audit_v1.py \
  | tee /tmp/equity_signal_generation_audit_v1.log

grep -q "EQUITY_SIGNAL_GENERATION_AUDIT_V1_OK" /tmp/equity_signal_generation_audit_v1.log
grep -q "EQUITY_SIGNAL_GENERATION_AUDIT_SUMMARY" /tmp/equity_signal_generation_audit_v1.log
grep -q "runtime_ok=" /tmp/equity_signal_generation_audit_v1.log
grep -q "bars_total=" /tmp/equity_signal_generation_audit_v1.log
grep -q "signals_total=" /tmp/equity_signal_generation_audit_v1.log
grep -q "VERDICT=" /tmp/equity_signal_generation_audit_v1.log
grep -q "db_update=0" /tmp/equity_signal_generation_audit_v1.log

echo
echo "=== EQUITY SIGNAL GENERATION SUMMARY ==="
grep -E "EQUITY_SIGNAL_GEN_RUNTIME_ROW|EQUITY_SIGNAL_GEN_BAR_ROW|EQUITY_SIGNAL_GEN_SIGNAL_ROW|EQUITY_SIGNAL_GEN_FEATURE_AUDIT_ROW|EQUITY_SIGNAL_GEN_BLOCK_ROW|EQUITY_SIGNAL_GEN_RISK_ROW|runtime_ok=|bars_total=|signals_total=|feature_audit_rows=|block_rows=|risk_rows=|existing_audit_tables=|VERDICT=" \
  /tmp/equity_signal_generation_audit_v1.log | head -160

echo TEST_EQUITY_SIGNAL_GENERATION_AUDIT_V1_OK
