#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY STRATEGY NAME RESOLVER AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/runtime/build_equity_strategy_name_resolver_audit_v1.py

PYTHONPATH=src python3 src/scripts/runtime/build_equity_strategy_name_resolver_audit_v1.py \
  | tee /tmp/equity_strategy_name_resolver_audit_v1.log

grep -q "EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_V1_OK" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "EQUITY_STRATEGY_NAME_RESOLVER_FUNCTION" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "EQUITY_STRATEGY_NAME_CALLS" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_SUMMARY" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "db_update=0" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "file_update=0" /tmp/equity_strategy_name_resolver_audit_v1.log
grep -q "VERDICT=" /tmp/equity_strategy_name_resolver_audit_v1.log

echo
echo "=== EQUITY STRATEGY NAME RESOLVER AUDIT SUMMARY ==="
grep -E "resolver_exists=|resolver_uses_symbol_map=|resolver_uses_runtime_active_universe=|call_at_runtime_add=|symbol_map_has_sber_volatility=|symbol_map_has_sber_trend=|symbol_map_default_mean=|mismatch_source_confirmed=|VERDICT=" \
  /tmp/equity_strategy_name_resolver_audit_v1.log

echo TEST_EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_V1_OK
