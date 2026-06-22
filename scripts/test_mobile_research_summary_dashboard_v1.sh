#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOBILE_RESEARCH_SUMMARY_DASHBOARD_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/mobile)"

echo "$html" | grep -q "Фьючерсы"
echo "$html" | grep -q "Акции"
echo "$html" | grep -q "RS Bottom Futures"
echo "$html" | grep -q "Equity RS Bottom Absolute"
echo "$html" | grep -q "Real Trading: 25%"
echo "$html" | grep -q "RS_BOTTOM_FIRST_COMPLETED_FORWARD_V1"

echo "VERDICT=MOBILE_RESEARCH_SUMMARY_DASHBOARD_OK"
echo "TEST_MOBILE_RESEARCH_SUMMARY_DASHBOARD_V1_OK"
