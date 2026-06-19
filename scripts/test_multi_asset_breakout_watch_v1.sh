#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT WATCH V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_watch_v1.py

PYTHONPATH=src python3 src/scripts/research/build_multi_asset_breakout_watch_v1.py \
  | tee /tmp/multi_asset_breakout_watch_v1.log

grep -q "MULTI_ASSET_BREAKOUT_WATCH_V1_OK" /tmp/multi_asset_breakout_watch_v1.log
grep -q "MULTI_ASSET_BREAKOUT_WATCH_SUMMARY" /tmp/multi_asset_breakout_watch_v1.log
grep -q "MULTI_ASSET_BREAKOUT_WATCH_ROW" /tmp/multi_asset_breakout_watch_v1.log
grep -q "breakout_ready=" /tmp/multi_asset_breakout_watch_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_watch_v1.log
grep -q "db_update=0" /tmp/multi_asset_breakout_watch_v1.log

echo
echo "=== MULTI ASSET BREAKOUT WATCH SUMMARY ==="
grep -E "MULTI_ASSET_BREAKOUT_WATCH_ROW|rows_total=|breakout_ready=|no_breakout=|atr_blocked=|volume_blocked=|VERDICT=" \
  /tmp/multi_asset_breakout_watch_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_WATCH_V1_OK
