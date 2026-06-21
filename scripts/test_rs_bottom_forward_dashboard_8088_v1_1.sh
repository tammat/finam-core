#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_DASHBOARD_8088_V1_1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/rs-bottom-forward)"

echo "$html" | grep -q "RS Bottom Forward Accumulation"
echo "$html" | grep -q "PF Historical"
echo "$html" | grep -q "Диагностика"

echo "VERDICT=RS_BOTTOM_FORWARD_DASHBOARD_8088_V1_1_OK"
echo "TEST_RS_BOTTOM_FORWARD_DASHBOARD_8088_V1_1_OK"
