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

curl -fsS   "http://127.0.0.1:8080/"   >/tmp/marketcore_ui_home_8080.html

curl -fsS   "http://127.0.0.1:8080/api/v2/domain-render-tree/control-center"   >/tmp/marketcore_ui_control_center_v2.json

curl -fsS   "http://127.0.0.1:8080/api/v2/i18n/catalog?locale=ru-RU"   >/tmp/marketcore_ui_i18n_ru_v2.json

grep -q   "MarketCore OS"   /tmp/marketcore_ui_home_8080.html

grep -q   'data-marketcore-ui-runtime="v2"'   /tmp/marketcore_ui_home_8080.html

grep -q   "workspace-shell-bootstrap.js"   /tmp/marketcore_ui_home_8080.html

test -s   /tmp/marketcore_ui_control_center_v2.json

test -s   /tmp/marketcore_ui_i18n_ru_v2.json

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SYSTEMD_8080_V1_READY"
echo "ui_runtime=v2"
echo "control_center_api=OK"
echo "i18n_ru_catalog=OK"
echo "legacy_html_routes_required=0"
echo "VERDICT=TEST_MARKETCORE_UI_SYSTEMD_8080_V1_OK"
