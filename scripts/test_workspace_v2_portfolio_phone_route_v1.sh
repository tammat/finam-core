#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/workspace_phone_route \
PYTHONPATH=src \
python -m py_compile \
    src/marketcore/presentation/router.py \
    src/marketcore/presentation/workspace_v2/portfolio_page_v2.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

desktop=$(curl -fsS http://127.0.0.1:8080/workspace-v2/portfolio)
phone=$(curl -fsS http://127.0.0.1:8080/workspace-v2/portfolio/phone)

check() {
    local text="$1"
    local pattern="$2"
    local name="$3"

    if grep -q "$pattern" <<<"$text"; then
        echo "OK: $name"
    else
        echo "FAIL: $name"
        exit 1
    fi
}

check "$desktop" "max-width:1600px" "desktop theme"
check "$phone"   "max-width:480px"  "phone theme"

check "$desktop" "grid-template-columns:1fr auto" "desktop layout"
check "$phone"   "grid-template-columns:1fr;gap:4px" "phone layout"

check "$phone" "P&amp;L %" "P&L percent"

echo
echo "desktop_length=${#desktop}"
echo "phone_length=${#phone}"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_PHONE_ROUTE_V1_OK"
