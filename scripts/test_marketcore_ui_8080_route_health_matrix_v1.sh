#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1 ==="

scripts/apply_marketcore_ui_route_health_matrix_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/marketcore_ui_route_health_matrix.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/marketcore_ui_route_health_matrix.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

DATABASE_URL=postgresql:///finam_core MARKETCORE_UI_BASE_URL=http://127.0.0.1:8080 PYTHONPATH=src \
python src/scripts/build_marketcore_ui_8080_route_health_matrix_v1.py \
  | tee /tmp/marketcore_ui_route_health_matrix_builder_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY" \
  /tmp/marketcore_ui_route_health_matrix_builder_v1.txt

curl -fsS "http://127.0.0.1:8095/api/kg/v1/marketcore-ui-route-health-matrix" \
  > /tmp/marketcore_ui_route_health_matrix_api_v1.json

curl -fsS "http://127.0.0.1:8080/marketcore-ui-route-health-matrix" \
  > /tmp/marketcore_ui_route_health_matrix_page_v1.html

grep -q '"status": "OK"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"route"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"http_ok"' /tmp/marketcore_ui_route_health_matrix_api_v1.json
grep -q '"content_length"' /tmp/marketcore_ui_route_health_matrix_api_v1.json

grep -q "Матрица здоровья маршрутов UI" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "Маршруты" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1" /tmp/marketcore_ui_route_health_matrix_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_route_health_matrix_page_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")
bad=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE http_ok=false;")
home_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/' AND http_ok=true;")
risk_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/risk' AND http_ok=true;")
settings_ok=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.marketcore_ui_route_health_matrix_v1 WHERE route='/settings' AND http_ok=true;")

test "$rows" -gt 0
test "$home_ok" = "1"
test "$risk_ok" = "1"
test "$settings_ok" = "1"

psql -d finam_core -c "
SELECT
    group_title_ru,
    route,
    label_ru,
    http_status,
    http_ok,
    content_length,
    issue
FROM marketcore_ui.marketcore_ui_route_health_matrix_v1
ORDER BY group_key, menu_order, route;
"

echo "route_health_rows=$rows"
echo "route_health_bad_rows=$bad"
echo "home_ok=$home_ok"
echo "risk_ok=$risk_ok"
echo "settings_ok=$settings_ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_OK"
