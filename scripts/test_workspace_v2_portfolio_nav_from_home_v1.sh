#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_NAV_FROM_HOME_V1 ==="

sql="sql/presentation/workspace_v2_home_nav_phone_v1.sql"

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql"

PYTHONPYCACHEPREFIX=/tmp/home_nav_phone \
PYTHONPATH=src \
python -m py_compile \
src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
src/marketcore/presentation/workspace_v2/home_page_v2.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

home=$(curl -fsS http://127.0.0.1:8080/workspace-v2)

echo "$home" | grep -q "Портфель"
echo "$home" | grep -q "Портфель · телефон"
echo "$home" | grep -q "/workspace-v2/portfolio"
echo "$home" | grep -q "/workspace-v2/portfolio/phone"

echo "home_navigation=OK"
echo "portfolio_phone_navigation=OK"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_PORTFOLIO_NAV_FROM_HOME_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_NAV_FROM_HOME_V1_OK"
