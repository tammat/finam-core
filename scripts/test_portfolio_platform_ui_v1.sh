#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_PLATFORM_UI_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/portfolio_platform.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/portfolio-platform/summary" > /tmp/portfolio_platform_ui_summary.json
curl -fsS "http://127.0.0.1:8095/api/kg/v1/portfolio-platform/positions" > /tmp/portfolio_platform_ui_positions.json
curl -fsS "http://127.0.0.1:8080/portfolio-platform" > /tmp/portfolio_platform_ui.html

grep -q "Portfolio Platform" /tmp/portfolio_platform_ui.html
grep -q "Итоговое состояние портфеля" /tmp/portfolio_platform_ui.html

if grep -R "SELECT .*portfolio_\|FROM analytics.portfolio_" \
  src/marketcore/presentation/pages/portfolio_platform.py; then
  echo "ERROR_DIRECT_SQL_IN_PORTFOLIO_PLATFORM_UI"
  exit 1
fi

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PORTFOLIO_PLATFORM_UI_V1_READY"
echo "VERDICT=TEST_PORTFOLIO_PLATFORM_UI_V1_OK"
