#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY CLOSED PNL 8088 INTEGRATION V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/ui/today_closed_pnl_widget_v1.py
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q '@app.get("/today-pnl"' src/ui/readonly_runtime_dashboard_v1.py
grep -q '@app.get("/today-pnl/json"' src/ui/readonly_runtime_dashboard_v1.py
grep -q 'render_today_closed_pnl_page_v1' src/ui/readonly_runtime_dashboard_v1.py
grep -q 'render_today_closed_pnl_json_v1' src/ui/readonly_runtime_dashboard_v1.py

echo "=== RESTART 8088 DASHBOARD ==="
sudo systemctl restart finam-core-ui-readonly.service

echo "=== WAIT FOR 8088 ==="
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8088/ >/tmp/today_pnl_8088_root.html; then
    echo "8088_READY attempt=${i}"
    break
  fi
  sleep 1
done

curl -fsS http://127.0.0.1:8088/today-pnl \
  | tee /tmp/today_pnl_8088.html \
  | head -40

grep -q "TODAY_CLOSED_PNL_STATUS_V1" /tmp/today_pnl_8088.html
grep -q "FINAM_CORE V3" /tmp/today_pnl_8088.html

curl -fsS http://127.0.0.1:8088/today-pnl/json \
  | tee /tmp/today_pnl_8088.json \
  | head -80

grep -q '"trades_today"' /tmp/today_pnl_8088.json
grep -q '"closed_cycles"' /tmp/today_pnl_8088.json
grep -q '"net_pnl"' /tmp/today_pnl_8088.json
grep -q '"real_trading_enabled": 0' /tmp/today_pnl_8088.json
grep -q '"execution_enabled": 0' /tmp/today_pnl_8088.json
grep -q '"runtime_allow": 0' /tmp/today_pnl_8088.json

echo
echo "=== TODAY PNL 8088 SUMMARY ==="
grep -E '"trades_today"|"closed_cycles"|"gross_pnl"|"commission"|"net_pnl"|"real_trading_enabled"|"verdict"' \
  /tmp/today_pnl_8088.json

echo TEST_TODAY_CLOSED_PNL_8088_INTEGRATION_V1_OK
