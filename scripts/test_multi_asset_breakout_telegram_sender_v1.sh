#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT TELEGRAM SENDER V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_telegram_sender_v1.py

PYTHONPATH=src FUTURES_PREFIXES="${FUTURES_PREFIXES:-BR,NG,GD}" MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/build_multi_asset_breakout_telegram_sender_v1.py \
  | tee /tmp/multi_asset_breakout_telegram_sender_v1.log

grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_V1_OK" /tmp/multi_asset_breakout_telegram_sender_v1.log
grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SUMMARY" /tmp/multi_asset_breakout_telegram_sender_v1.log
grep -q "telegram_dry_run=1" /tmp/multi_asset_breakout_telegram_sender_v1.log
grep -q "telegram_sent=0" /tmp/multi_asset_breakout_telegram_sender_v1.log
grep -q "db_update=0" /tmp/multi_asset_breakout_telegram_sender_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_telegram_sender_v1.log

echo "=== MULTI ASSET BREAKOUT TELEGRAM SENDER SUMMARY ==="
grep -E "plan_ok=|telegram_decision=|ready_rows=|telegram_dry_run=|telegram_sent=|telegram_skipped=|VERDICT=" \
  /tmp/multi_asset_breakout_telegram_sender_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_V1_OK
