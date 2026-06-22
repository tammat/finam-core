#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BRENT_ROLLOVER_EDGE_DASHBOARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py
python3 -m py_compile src/scripts/research/build_brent_rollover_edge_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/brent-rollover-edge)"

echo "$html" | grep -q "Brent Rollover Edge"
echo "$html" | grep -q "BOTTOM1 + COMPRESSION_RANGE + 240m"
echo "$html" | grep -q "Автообновление"
echo "$html" | grep -q "BRQ6"
echo "$html" | grep -q "BRENT_ROLLOVER"

echo "VERDICT=BRENT_ROLLOVER_EDGE_DASHBOARD_8088_OK"
echo "TEST_BRENT_ROLLOVER_EDGE_DASHBOARD_8088_V1_OK"
