#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_MONITOR_MOBILE_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/mobile)"

echo "$html" | grep -q "ТЕКУЩИЙ КАНДИДАТ НА EDGE"
echo "$html" | grep -q "RS Bottom Futures"
echo "$html" | grep -q "BRQ6"
echo "$html" | grep -q "NGV6"
echo "$html" | grep -q "GLM6"
echo "$html" | grep -q "CONTRACT_SPECIFIC_ANOMALY"
echo "$html" | grep -q "RS_BOTTOM_FIRST_COMPLETED_FORWARD_V1"

echo "VERDICT=EDGE_MONITOR_MOBILE_OK"
echo "TEST_EDGE_MONITOR_MOBILE_V1_OK"
