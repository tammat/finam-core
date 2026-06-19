#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET FX WATCHLIST APPLY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_watch_v2.py
python3 -m py_compile src/finam_core/strategy/instrument_profile.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_watch_v2.py \
  | tee /tmp/multi_asset_fx_watchlist_apply_v1.log

grep -q "MULTI_ASSET_BREAKOUT_WATCH_V2_OK" /tmp/multi_asset_fx_watchlist_apply_v1.log

grep -q "symbol=USDRUBF@RTSX family=FX_FUTURES timeframe=M5 role=PRIMARY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "symbol=USDRUBF@RTSX family=FX_FUTURES timeframe=M1 role=INTRADAY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "symbol=CNYRUBF@RTSX family=FX_FUTURES timeframe=M5 role=PRIMARY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "symbol=CNYRUBF@RTSX family=FX_FUTURES timeframe=M1 role=INTRADAY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "symbol=CNYRUB_TOM@MISX family=FX_SPOT timeframe=M5 role=PRIMARY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "symbol=CNYRUB_TOM@MISX family=FX_SPOT timeframe=M1 role=INTRADAY_WATCH" /tmp/multi_asset_fx_watchlist_apply_v1.log

grep -q "MULTI_ASSET_BREAKOUT_WATCH_V2_ROW symbol=USDRUBF@RTSX" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "MULTI_ASSET_BREAKOUT_WATCH_V2_ROW symbol=CNYRUBF@RTSX" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "MULTI_ASSET_BREAKOUT_WATCH_V2_ROW symbol=CNYRUB_TOM@MISX" /tmp/multi_asset_fx_watchlist_apply_v1.log

grep -q "orders_create=0" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "runtime_changes_required=0" /tmp/multi_asset_fx_watchlist_apply_v1.log
grep -q "execution_changes_required=0" /tmp/multi_asset_fx_watchlist_apply_v1.log

echo "=== FX WATCHLIST APPLY SUMMARY ==="
grep -E "symbol=USDRUBF@RTSX|symbol=CNYRUBF@RTSX|symbol=CNYRUB_TOM@MISX|universe_total=|rows_total=|VERDICT=" \
  /tmp/multi_asset_fx_watchlist_apply_v1.log

echo "VERDICT=MULTI_ASSET_FX_WATCHLIST_APPLY_READY"
echo TEST_MULTI_ASSET_FX_WATCHLIST_APPLY_V1_OK
