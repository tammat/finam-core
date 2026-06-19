#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT FOLLOW THROUGH DASHBOARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18088 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_follow_through_dashboard_v1.log 2>&1 &
PID=$!

sleep 3

curl -fsS http://127.0.0.1:18088/api/current | tee /tmp/multi_asset_follow_through_dashboard_v1.json >/dev/null
curl -fsS http://127.0.0.1:18088/ | tee /tmp/multi_asset_follow_through_dashboard_v1.html >/dev/null

kill "$PID"
wait "$PID" 2>/dev/null || true

grep -q '"follow_through"' /tmp/multi_asset_follow_through_dashboard_v1.json
grep -q '"ready_rows"' /tmp/multi_asset_follow_through_dashboard_v1.json
grep -q '"scorecard_rows_total"' /tmp/multi_asset_follow_through_dashboard_v1.json
grep -q '"waiting_rows"' /tmp/multi_asset_follow_through_dashboard_v1.json
grep -q '"execution_enabled": "0"' /tmp/multi_asset_follow_through_dashboard_v1.json
grep -q '"real_trading_enabled": "0"' /tmp/multi_asset_follow_through_dashboard_v1.json

grep -q "Follow-through scorecard" /tmp/multi_asset_follow_through_dashboard_v1.html
grep -q "BREAKOUT_READY всего" /tmp/multi_asset_follow_through_dashboard_v1.html
grep -q "Горизонты 3/5/10/15 минут" /tmp/multi_asset_follow_through_dashboard_v1.html
grep -q "По инструментам" /tmp/multi_asset_follow_through_dashboard_v1.html

echo "=== FOLLOW THROUGH DASHBOARD SUMMARY ==="
grep -E '"follow_through"|"ready_rows"|"scorecard_rows_total"|"waiting_rows"|"execution_enabled"|"real_trading_enabled"' \
  /tmp/multi_asset_follow_through_dashboard_v1.json

echo "VERDICT=MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_DASHBOARD_READY"
echo TEST_MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_DASHBOARD_V1_OK
