#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ACTIVE_FUTURES_UNIVERSE_LIVE_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/active-futures-universe" \
  | tee /tmp/active_futures_universe_live_8088_v1.html >/dev/null

grep -q "Active Futures Universe Live V1" /tmp/active_futures_universe_live_8088_v1.html
grep -q "Live-окно" /tmp/active_futures_universe_live_8088_v1.html
grep -q "Автообновление" /tmp/active_futures_universe_live_8088_v1.html
grep -q "Live completed 24h" /tmp/active_futures_universe_live_8088_v1.html
grep -q "As of" /tmp/active_futures_universe_live_8088_v1.html

echo "TEST_ACTIVE_FUTURES_UNIVERSE_LIVE_8088_V1_OK"
