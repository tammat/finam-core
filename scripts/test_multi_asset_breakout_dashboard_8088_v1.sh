#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST MULTI ASSET BREAKOUT DASHBOARD 8088 V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "db_update=0"

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

grep -q "MULTI_ASSET_DASHBOARD_PORT=8088" deploy/systemd/finam-multi-asset-breakout-dashboard.service
grep -q "EXECUTION_ENABLED=0" deploy/systemd/finam-multi-asset-breakout-dashboard.service
grep -q "REAL_TRADING_ENABLED=0" deploy/systemd/finam-multi-asset-breakout-dashboard.service
grep -q "RUNTIME_ALLOW_TRADING=0" deploy/systemd/finam-multi-asset-breakout-dashboard.service
grep -q "serve_multi_asset_breakout_dashboard_v1.py" deploy/systemd/finam-multi-asset-breakout-dashboard.service

systemd-analyze verify /etc/systemd/system/finam-multi-asset-breakout-telegram.service
systemd-analyze verify deploy/systemd/finam-multi-asset-breakout-dashboard.service

PYTHONPATH=src MULTI_ASSET_DASHBOARD_PORT=18088 \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 MULTI_ASSET_TELEGRAM_DRY_RUN=1 \
python3 src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py >/tmp/multi_asset_dashboard_8088_v1.log 2>&1 &
PID=$!

sleep 3

curl -fsS http://127.0.0.1:18088/api/current | tee /tmp/multi_asset_dashboard_8088_v1.json >/dev/null

kill "$PID"
wait "$PID" 2>/dev/null || true

grep -q '"dashboard": "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_OBSERVATION_V1"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"execution_enabled": "0"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"real_trading_enabled": "0"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"telegram_dry_run": "1"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"summary"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"blocker_counts"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"ready_rows"' /tmp/multi_asset_dashboard_8088_v1.json
grep -q '"rows"' /tmp/multi_asset_dashboard_8088_v1.json

echo "=== DASHBOARD JSON SUMMARY ==="
grep -E '"dashboard"|"universe_total"|"rows_total"|"breakout_ready"|"telegram_decision"|"v2_verdict"|"plan_verdict"|"execution_enabled"|"real_trading_enabled"' \
  /tmp/multi_asset_dashboard_8088_v1.json

echo "VERDICT=MULTI_ASSET_BREAKOUT_DASHBOARD_8088_PLAN_READY"
echo TEST_MULTI_ASSET_BREAKOUT_DASHBOARD_8088_V1_OK
