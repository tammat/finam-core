#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST EQUITY MARKET BARS SYMBOL ALIAS AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_equity_market_bars_symbol_alias_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_equity_market_bars_symbol_alias_audit_v1.py \
  | tee /tmp/equity_market_bars_symbol_alias_audit_v1.log

grep -q "EQUITY_MARKET_BARS_SYMBOL_ALIAS_AUDIT_V1_OK" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "EXACT_ALIAS_CANDIDATES" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "FUZZY_SYMBOL_SEARCH" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "RUNTIME_ROWS" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "orders_create=0" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "execution_intents_create=0" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "execution_enabled=0" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "real_trading_enabled=0" /tmp/equity_market_bars_symbol_alias_audit_v1.log
grep -q "VERDICT=EQUITY_MARKET_BARS_SYMBOL_ALIAS_AUDIT_READY" /tmp/equity_market_bars_symbol_alias_audit_v1.log

echo "=== EQUITY ALIAS AUDIT SUMMARY ==="
grep -E "ALIAS_ROW|FUZZY_ROW|RUNTIME_ROW|VERDICT=" \
  /tmp/equity_market_bars_symbol_alias_audit_v1.log

echo TEST_EQUITY_MARKET_BARS_SYMBOL_ALIAS_AUDIT_V1_OK
