#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT READY EVENT DELIVERY DASHBOARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18090 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_ready_delivery_dashboard_v1.log 2>&1 &
PID=$!

sleep 3

curl --max-time 10 -fsS http://127.0.0.1:18090/api/current | tee /tmp/multi_asset_ready_delivery_dashboard_v1.json >/dev/null
curl --max-time 10 -fsS http://127.0.0.1:18090/delivery | tee /tmp/multi_asset_ready_delivery_dashboard_v1.html >/dev/null

kill "$PID"
wait "$PID" 2>/dev/null || true

grep -q '"ready_delivery"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"ready_total"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"delivery_total"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"dry_run_total"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"undelivered_ready"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"execution_enabled": "0"' /tmp/multi_asset_ready_delivery_dashboard_v1.json
grep -q '"real_trading_enabled": "0"' /tmp/multi_asset_ready_delivery_dashboard_v1.json

grep -q "Доставка BREAKOUT_READY" /tmp/multi_asset_ready_delivery_dashboard_v1.html
grep -q "ready всего" /tmp/multi_asset_ready_delivery_dashboard_v1.html
grep -q "доставлено всего" /tmp/multi_asset_ready_delivery_dashboard_v1.html
grep -q "новых недоставленных ready" /tmp/multi_asset_ready_delivery_dashboard_v1.html

echo "=== READY DELIVERY DASHBOARD SUMMARY ==="
grep -E '"ready_delivery"|"ready_total"|"delivery_total"|"dry_run_total"|"undelivered_ready"|"execution_enabled"|"real_trading_enabled"' \
  /tmp/multi_asset_ready_delivery_dashboard_v1.json

echo "VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_DASHBOARD_READY"
echo TEST_MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_DASHBOARD_V1_OK
