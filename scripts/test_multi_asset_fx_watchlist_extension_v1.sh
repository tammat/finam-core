#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET FX WATCHLIST EXTENSION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_fx_watchlist_extension_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_fx_watchlist_extension_v1.py \
  | tee /tmp/multi_asset_fx_watchlist_extension_v1.log

grep -q "MULTI_ASSET_FX_WATCHLIST_EXTENSION_V1_OK" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "symbol=USDRUBF@RTSX" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "symbol=CNYRUBF@RTSX" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "symbol=CNYRUB_TOM@MISX" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "logical_name=CNYRUB_TOD status=NO_MARKET_BARS" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "logical_name=IMOEX status=NO_MARKET_BARS" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "orders_create=0" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_fx_watchlist_extension_v1.log
grep -q "VERDICT=MULTI_ASSET_FX_WATCHLIST_EXTENSION_PLAN_READY" /tmp/multi_asset_fx_watchlist_extension_v1.log

echo "=== FX WATCHLIST EXTENSION SUMMARY ==="
grep -E "FX_WATCHLIST_ROW|FX_MISSING_ROW|planned_rows=|blocked_rows=|missing_context_rows=|VERDICT=" \
  /tmp/multi_asset_fx_watchlist_extension_v1.log

echo TEST_MULTI_ASSET_FX_WATCHLIST_EXTENSION_V1_OK
