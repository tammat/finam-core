#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET SIGNAL WATCH PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/finam_core/strategy/instrument_profile.py \
  src/scripts/research/build_multi_asset_signal_watch_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_multi_asset_signal_watch_plan_v1.py \
  | tee /tmp/multi_asset_signal_watch_plan_v1.log

grep -q "MULTI_ASSET_SIGNAL_WATCH_PLAN_V1_OK" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "MULTI_ASSET_SIGNAL_WATCH_PLAN_SUMMARY" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "MULTI_ASSET_SIGNAL_WATCH_PROFILE_ROW" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "atr_min_pct=" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "volume_mult=" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "VERDICT=" /tmp/multi_asset_signal_watch_plan_v1.log
grep -q "db_update=0" /tmp/multi_asset_signal_watch_plan_v1.log

echo
echo "=== MULTI ASSET SIGNAL WATCH PLAN SUMMARY ==="
grep -E "MULTI_ASSET_SIGNAL_WATCH_PROFILE_ROW|rows_total=|equity_rows=|futures_rows=|index_rows=|unknown_rows=|VERDICT=" \
  /tmp/multi_asset_signal_watch_plan_v1.log

echo TEST_MULTI_ASSET_SIGNAL_WATCH_PLAN_V1_OK
