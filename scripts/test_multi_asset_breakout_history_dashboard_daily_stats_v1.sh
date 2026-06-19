#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT HISTORY DASHBOARD DAILY STATS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18088 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_history_dashboard_daily_stats_v1.log 2>&1 &
PID=$!

sleep 3

curl -fsS http://127.0.0.1:18088/api/current | tee /tmp/multi_asset_history_dashboard_daily_stats_v1.json >/dev/null
curl -fsS http://127.0.0.1:18088/ | tee /tmp/multi_asset_history_dashboard_daily_stats_v1.html >/dev/null

kill "$PID"
wait "$PID" 2>/dev/null || true

grep -q '"dashboard": "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_OBSERVATION_V1"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"history_daily"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"snapshots_today"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"rows_today"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"ready_today"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"execution_enabled": "0"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json
grep -q '"real_trading_enabled": "0"' /tmp/multi_asset_history_dashboard_daily_stats_v1.json

grep -q "История за день" /tmp/multi_asset_history_dashboard_daily_stats_v1.html
grep -q "снимков сегодня" /tmp/multi_asset_history_dashboard_daily_stats_v1.html
grep -q "строк наблюдения сегодня" /tmp/multi_asset_history_dashboard_daily_stats_v1.html
grep -q "Статистика по инструментам" /tmp/multi_asset_history_dashboard_daily_stats_v1.html
grep -q "Сводка" /tmp/multi_asset_history_dashboard_daily_stats_v1.html
grep -q "API JSON" /tmp/multi_asset_history_dashboard_daily_stats_v1.html

echo "=== HISTORY DASHBOARD DAILY STATS SUMMARY ==="
grep -E '"history_daily"|"snapshots_today"|"rows_today"|"ready_today"|"execution_enabled"|"real_trading_enabled"' \
  /tmp/multi_asset_history_dashboard_daily_stats_v1.json

echo "VERDICT=MULTI_ASSET_BREAKOUT_HISTORY_DASHBOARD_DAILY_STATS_READY"
echo TEST_MULTI_ASSET_BREAKOUT_HISTORY_DASHBOARD_DAILY_STATS_V1_OK
