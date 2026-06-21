#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_PAPER_DASHBOARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/rs-bottom-paper)"

echo "$html" | grep -q "RS Bottom Paper"
echo "$html" | grep -q "signals_total"
echo "$html" | grep -q "WAITING"
echo "$html" | grep -q "Historical Edge Reference"
echo "$html" | grep -q "BOTTOM1 + COMPRESSION_RANGE"

echo "VERDICT=RS_BOTTOM_PAPER_DASHBOARD_8088_OK"
echo "TEST_RS_BOTTOM_PAPER_DASHBOARD_8088_V1_OK"
