#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY VOLATILITY GATE AFTER PATCH VALIDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_equity_volatility_gate_after_patch_validation_v1.py

PYTHONPATH=src python3 src/scripts/research/build_equity_volatility_gate_after_patch_validation_v1.py \
  | tee /tmp/equity_volatility_gate_after_patch_validation_v1.log

grep -q "EQUITY_VOLATILITY_GATE_AFTER_PATCH_VALIDATION_V1_OK" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "EQUITY_VOLATILITY_GATE_AFTER_PATCH_SUMMARY" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "fresh_guard_rows=" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "equity_volatility_reason_rows=" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "br_volatility_reason_rows=" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "VERDICT=" /tmp/equity_volatility_gate_after_patch_validation_v1.log
grep -q "db_update=0" /tmp/equity_volatility_gate_after_patch_validation_v1.log

echo
echo "=== EQUITY VOLATILITY GATE AFTER PATCH SUMMARY ==="
grep -E "EQUITY_AFTER_PATCH_GUARD_ROW|fresh_guard_rows=|fresh_signals=|equity_volatility_reason_rows=|br_volatility_reason_rows=|expected_threshold_rows=|wrong_threshold_rows=|compression_watch_rows=|VERDICT=" \
  /tmp/equity_volatility_gate_after_patch_validation_v1.log | head -160

echo TEST_EQUITY_VOLATILITY_GATE_AFTER_PATCH_VALIDATION_V1_OK
