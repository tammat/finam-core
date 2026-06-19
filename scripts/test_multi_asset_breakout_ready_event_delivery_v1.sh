#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT READY EVENT DELIVERY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "orders_create=0"
echo "execution_intents_create=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_ready_event_delivery_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
MULTI_ASSET_READY_EVENT_DRY_RUN=1 \
python3 src/scripts/research/build_multi_asset_breakout_ready_event_delivery_v1.py \
  | tee /tmp/multi_asset_breakout_ready_event_delivery_v1.log

grep -q "MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_V1_OK" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_SUMMARY" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "delivery_dry_run=1" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "orders_create=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "execution_intents_create=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "runtime_changes_required=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "execution_changes_required=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "real_trading_enabled=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "execution_enabled=0" /tmp/multi_asset_breakout_ready_event_delivery_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_ready_event_delivery_v1.log

echo "=== READY EVENT DELIVERY SUMMARY ==="
grep -E "ready_total=|undelivered_before=|delivery_total=|dry_run_total=|delivered=|skipped=|delivery_dry_run=|VERDICT=" \
  /tmp/multi_asset_breakout_ready_event_delivery_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_V1_OK
