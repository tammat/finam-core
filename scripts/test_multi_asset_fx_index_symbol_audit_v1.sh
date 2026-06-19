#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET FX INDEX SYMBOL AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_fx_index_symbol_audit_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_fx_index_symbol_audit_v1.py \
  | tee /tmp/multi_asset_fx_index_symbol_audit_v1.log

grep -q "MULTI_ASSET_FX_INDEX_SYMBOL_AUDIT_V1_OK" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "selected_USDRUBF=" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "selected_CNYRUB_TOD=" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "selected_IMOEX=" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "orders_create=0" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_fx_index_symbol_audit_v1.log
grep -q "VERDICT=" /tmp/multi_asset_fx_index_symbol_audit_v1.log

echo "=== FX INDEX SYMBOL AUDIT SUMMARY ==="
grep -E "SYMBOL_SELECTED_ROW|selected_USDRUBF=|selected_CNYRUB_TOD=|selected_IMOEX=|VERDICT=" \
  /tmp/multi_asset_fx_index_symbol_audit_v1.log

echo TEST_MULTI_ASSET_FX_INDEX_SYMBOL_AUDIT_V1_OK
