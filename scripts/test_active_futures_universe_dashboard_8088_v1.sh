#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ACTIVE_FUTURES_UNIVERSE_DASHBOARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/active-futures-universe" \
  | tee /tmp/active_futures_universe_dashboard_8088_v1.html >/dev/null

grep -q "Active Futures Universe V1" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "Runtime recommendation" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "PRIMARY" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "SECONDARY" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "WATCH_ONLY" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "REJECT" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "NGM6@RTSX" /tmp/active_futures_universe_dashboard_8088_v1.html
grep -q "GDU6@RTSX" /tmp/active_futures_universe_dashboard_8088_v1.html

echo "TEST_ACTIVE_FUTURES_UNIVERSE_DASHBOARD_8088_V1_OK"
