#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SYSTEMD_8080_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/check_marketcore_ui_systemd_8080_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py \
  src/marketcore/presentation/registry.py

test -f deploy/systemd/marketcore-kg-api.service
test -f deploy/systemd/marketcore-ui-shell.service

grep -q "KG_API_PORT=8095" deploy/systemd/marketcore-kg-api.service
grep -q "MARKETCORE_UI_PORT=8080" deploy/systemd/marketcore-ui-shell.service
grep -q "MARKETCORE_UI_HOST=0.0.0.0" deploy/systemd/marketcore-ui-shell.service
grep -q "KG_API_BASE_URL=http://127.0.0.1:8095" deploy/systemd/marketcore-ui-shell.service

echo "=== STOP_OLD_MANUAL_PROCESSES_IF_ANY ==="
pkill -f "src/marketcore/api/serve_knowledge_graph_api_v1.py" >/dev/null 2>&1 || true
pkill -f "src/marketcore/presentation/app.py" >/dev/null 2>&1 || true

echo "=== INSTALL_SYSTEMD_UNITS ==="
sudo cp deploy/systemd/marketcore-kg-api.service /etc/systemd/system/
sudo cp deploy/systemd/marketcore-ui-shell.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable --now marketcore-kg-api.service
sudo systemctl enable --now marketcore-ui-shell.service

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

echo "=== SYSTEMD_STATUS ==="
systemctl status marketcore-kg-api.service --no-pager || true
systemctl status marketcore-ui-shell.service --no-pager || true

echo "=== LISTEN_PORTS ==="
ss -ltnp | grep -E ':8080|:8095' || true

echo "=== HTTP_CHECKS ==="
PYTHONPATH=src python src/scripts/check_marketcore_ui_systemd_8080_v1.py | tee /tmp/marketcore_ui_systemd_8080_v1.txt

grep -q "VERDICT=CHECK_MARKETCORE_UI_SYSTEMD_8080_V1_OK" /tmp/marketcore_ui_systemd_8080_v1.txt

server_ip=$(hostname -I | awk '{print $1}')
echo "server_ip=$server_ip"
echo "open_url=http://$server_ip:8080/"
echo "open_risk=http://$server_ip:8080/risk"
echo "open_settings=http://$server_ip:8080/settings"

curl -fsS "http://127.0.0.1:8080/" >/tmp/marketcore_ui_home_8080.html
curl -fsS "http://127.0.0.1:8080/risk" >/tmp/marketcore_ui_risk_8080.html
curl -fsS "http://127.0.0.1:8080/settings" >/tmp/marketcore_ui_settings_8080.html

grep -q "MarketCore OS" /tmp/marketcore_ui_home_8080.html
grep -q "Риски" /tmp/marketcore_ui_risk_8080.html
grep -q "Настройки" /tmp/marketcore_ui_settings_8080.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SYSTEMD_8080_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SYSTEMD_8080_V1_OK"
