#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SERVICE="deploy/systemd/finam-multi-asset-breakout-telegram.service"
TIMER="deploy/systemd/finam-multi-asset-breakout-telegram.timer"

echo "=== TEST MULTI ASSET BREAKOUT TELEGRAM SYSTEMD PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "systemd_install=0"
echo "systemd_enable=0"
echo "telegram_real_send=0"

test -f "$SERVICE"
test -f "$TIMER"

grep -q "build_multi_asset_breakout_telegram_sender_v1.py" "$SERVICE"
grep -q "MULTI_ASSET_TELEGRAM_DRY_RUN=0" "$SERVICE"
grep -q "RUNTIME_ALLOW_TRADING=0" "$SERVICE"
grep -q "EXECUTION_ENABLED=0" "$SERVICE"
grep -q "REAL_TRADING_ENABLED=0" "$SERVICE"
grep -q "FUTURES_PREFIXES=BR,NG,GD" "$SERVICE"
grep -q "EnvironmentFile=/opt/finam-core/deploy/env/.env" "$SERVICE"

grep -q "OnUnitActiveSec=5min" "$TIMER"
grep -q "Persistent=true" "$TIMER"
grep -q "Unit=finam-multi-asset-breakout-telegram.service" "$TIMER"

systemd-analyze verify "$SERVICE" "$TIMER"

PYTHONPATH=src FUTURES_PREFIXES=BR,NG,GD MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_breakout_telegram_sender_v1.py \
  | tee /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log

grep -q "MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_V1_OK" /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log
grep -q "telegram_dry_run=1" /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log
grep -q "telegram_sent=0" /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log
grep -q "db_update=0" /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log
grep -q "VERDICT=" /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log

echo "=== MULTI ASSET BREAKOUT TELEGRAM SYSTEMD PLAN SUMMARY ==="
grep -E "plan_ok=|telegram_decision=|ready_rows=|telegram_dry_run=|telegram_sent=|telegram_skipped=|VERDICT=" \
  /tmp/multi_asset_breakout_telegram_systemd_plan_v1.log

echo "VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_PLAN_READY"
echo TEST_MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_PLAN_V1_OK
