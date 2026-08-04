#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT TELEGRAM SYSTEMD RUNTIME VALIDATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "db_update=0"
echo "telegram_notification_send_enabled=1"

python3 -m py_compile src/scripts/research/build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py

PYTHONPATH=src SINCE="${SINCE:-2026-06-19 13:39:00}" \
python3 src/scripts/research/build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py \
  | tee /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log

grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_V1_OK" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_SUMMARY" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "timer_active=1" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "timer_enabled=1" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "last_execution_enabled=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "last_real_trading_enabled=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "last_telegram_dry_run=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "execution_bad_lines=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "real_trading_bad_lines=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "tracebacks=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "errors=0" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log
grep -q "VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_OK" /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log

echo "=== MULTI ASSET BREAKOUT TELEGRAM SYSTEMD RUNTIME VALIDATION SUMMARY ==="
grep -E "timer_|service_success=|last_|execution_bad_lines=|real_trading_bad_lines=|tracebacks=|errors=|VERDICT=" \
  /tmp/multi_asset_breakout_telegram_systemd_runtime_validation_v1.log

echo TEST_MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_V1_OK
