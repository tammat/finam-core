#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BREAKOUT_CONFIRMATION_DASHBOARD_8088_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/rs-breakout-confirmation)"

echo "$html" | grep -q "RS Breakout Confirmation"
echo "$html" | grep -q "Окно подтверждения"
echo "$html" | grep -q "Диагностика: <b>OK</b>"
echo "$html" | grep -q "Корзина"
echo "$html" | grep -q "RS_ONLY"

echo "VERDICT=RS_BREAKOUT_CONFIRMATION_DASHBOARD_8088_OK"
echo "TEST_RS_BREAKOUT_CONFIRMATION_DASHBOARD_8088_V1_OK"
