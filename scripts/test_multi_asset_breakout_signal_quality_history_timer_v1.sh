#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

SERVICE="deploy/systemd/finam-multi-asset-breakout-history.service"
TIMER="deploy/systemd/finam-multi-asset-breakout-history.timer"

echo "=== TEST MULTI ASSET BREAKOUT SIGNAL QUALITY HISTORY TIMER V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "db_update=1"
echo "real_execution=0"

test -f "$SERVICE"
test -f "$TIMER"

grep -q "build_multi_asset_breakout_signal_quality_history_v1.py --migrate --save" "$SERVICE"
grep -q "RUNTIME_ALLOW_TRADING=0" "$SERVICE"
grep -q "EXECUTION_ENABLED=0" "$SERVICE"
grep -q "REAL_TRADING_ENABLED=0" "$SERVICE"
grep -q "FUTURES_PREFIXES=BR,NG,GD" "$SERVICE"
grep -q "EnvironmentFile=/opt/finam-core/deploy/env/.env" "$SERVICE"

grep -q "OnCalendar=\*-\*-\* 00:40:00 Europe/Moscow" "$TIMER"
grep -q "Persistent=true" "$TIMER"
grep -q "Unit=finam-multi-asset-breakout-history.service" "$TIMER"

systemd-analyze verify "$SERVICE" "$TIMER"

grep -q "is_market_opening_guard" src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py
grep -q "PROTECTED_MARKET_OPEN_WINDOW" src/scripts/research/build_multi_asset_breakout_signal_quality_history_v1.py

echo "VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_TIMER_READY"
echo TEST_MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_TIMER_V1_OK
