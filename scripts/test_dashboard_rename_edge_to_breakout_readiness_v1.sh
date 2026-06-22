#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_RENAME_EDGE_TO_BREAKOUT_READINESS_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/edge)"

echo "$html" | grep -q "Техническая готовность к пробою"
echo "$html" | grep -q "Это не подтверждённый торговый edge"
echo "$html" | grep -q "Постконтроль"

if echo "$html" | grep -q "Рейтинг Edge"; then
  echo "OLD_EDGE_TITLE_FOUND=1"
  exit 1
fi

echo "VERDICT=DASHBOARD_RENAME_EDGE_TO_BREAKOUT_READINESS_OK"
echo "TEST_DASHBOARD_RENAME_EDGE_TO_BREAKOUT_READINESS_V1_OK"
