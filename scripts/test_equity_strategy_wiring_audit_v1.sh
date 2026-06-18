#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY WIRING AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_wiring_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_wiring_audit_v1.py \
  | tee /tmp/equity_strategy_wiring_audit_v1.log

grep -q "EQUITY_STRATEGY_WIRING_AUDIT_V1_OK" /tmp/equity_strategy_wiring_audit_v1.log
grep -q "EQUITY_STRATEGY_WIRING_FILE_ROWS" /tmp/equity_strategy_wiring_audit_v1.log
grep -q "EQUITY_STRATEGY_WIRING_PATTERN_ROWS" /tmp/equity_strategy_wiring_audit_v1.log
grep -q "EQUITY_STRATEGY_WIRING_AUDIT_SUMMARY" /tmp/equity_strategy_wiring_audit_v1.log
grep -q "db_update=0" /tmp/equity_strategy_wiring_audit_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_wiring_audit_v1.log

echo
echo "=== EQUITY STRATEGY WIRING AUDIT SUMMARY ==="
grep -E "factory_supports_volatility=|volatility_class_exists=|paper_imports_strategy_factory=|paper_imports_volatility=|paper_uses_volatility_name=|paper_uses_mean_reversion=|symbol_map_legacy_bias=|wiring_mismatch=|VERDICT=" \
  /tmp/equity_strategy_wiring_audit_v1.log

echo TEST_EQUITY_STRATEGY_WIRING_AUDIT_V1_OK
