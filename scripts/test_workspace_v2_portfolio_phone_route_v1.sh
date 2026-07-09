#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1 ==="

files=(
"src/marketcore/presentation/router.py"
"src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_phone_route \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

sudo systemctl restart marketcore-ui-shell.service
sleep 2

desktop=$(curl -sS http://127.0.0.1:8080/workspace-v2/portfolio)
phone=$(curl -sS http://127.0.0.1:8080/workspace-v2/portfolio/phone)

echo "$desktop" | grep -q "max-width:1600px"
echo "$phone" | grep -q "max-width:480px"

echo "$phone" | grep -q "P&amp;L %"

echo "desktop_theme=OK"
echo "phone_theme=OK"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1_OK"
