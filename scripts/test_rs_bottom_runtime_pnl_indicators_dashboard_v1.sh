#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RS_BOTTOM_RUNTIME_PNL_INDICATORS_DASHBOARD_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html >/dev/null

grep -q "Индикаторы" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "Состояние edge" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "PnL всего" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "PnL средний" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "Макс. просадка" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "Средний результат" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "GDU6@RTSX" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "GLU6@RTSX" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html
grep -q "NGM6@RTSX" /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html

if grep -Eq '[0-9]+\.[0-9]{8,}' /tmp/rs_bottom_runtime_pnl_indicators_dashboard_v1.html; then
  echo "VERDICT=RS_BOTTOM_RUNTIME_PNL_INDICATORS_HAS_LONG_DECIMALS"
  exit 1
fi

echo "VERDICT=RS_BOTTOM_RUNTIME_PNL_INDICATORS_DASHBOARD_OK"
echo "TEST_RS_BOTTOM_RUNTIME_PNL_INDICATORS_DASHBOARD_V1_OK"
