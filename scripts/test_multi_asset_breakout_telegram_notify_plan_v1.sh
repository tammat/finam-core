#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT TELEGRAM NOTIFY PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_telegram_notify_plan_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" \
python3 src/scripts/research/build_multi_asset_breakout_telegram_notify_plan_v1.py \
  | tee /tmp/multi_asset_breakout_telegram_notify_plan_v1.log

grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V1_OK" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_SUMMARY" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "telegram_decision=" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "telegram_send=0" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "breakout_ready=" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log
grep -q "db_update=0" /tmp/multi_asset_breakout_telegram_notify_plan_v1.log

echo "=== MULTI ASSET BREAKOUT TELEGRAM NOTIFY PLAN SUMMARY ==="
grep -E "v2_|MULTI_ASSET_BREAKOUT_TELEGRAM_READY_ROW|TELEGRAM_MESSAGE|breakout_ready=|ready_rows=|telegram_decision=|telegram_send=|VERDICT=" \
  /tmp/multi_asset_breakout_telegram_notify_plan_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V1_OK
